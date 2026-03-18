"""Determinism tests for Cognee adapter.

These tests validate that the Cognee adapter produces identical results
across multiple runs with the same input data. Per TOML specification:
- Same data ingested twice → same node IDs
- Same query → same results
- Graph write idempotency
- Embedding consistency

Any non-determinism will cause these tests to fail.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Mark all tests in this file with 'determinism' marker
pytestmark = [
    pytest.mark.determinism,
    pytest.mark.asyncio,
]


class TestCogneeIdempotency:
    """Test Cognee adapter idempotency - same input → same output."""

    @pytest.fixture
    def sample_courses(self) -> List[Dict[str, Any]]:
        """Create deterministic test courses."""
        return [
            {
                "id": "course-math-101",
                "name": "Mathematics 101",
                "description": "Introduction to calculus and algebra",
                "department": "MATH",
                "credits": 3,
                "math_intensity": 0.95,
                "humanities_intensity": 0.1,
                "career_paths": ["data_scientist", "engineer"],
            },
            {
                "id": "course-cs-101",
                "name": "Computer Science Fundamentals",
                "description": "Introduction to programming and algorithms",
                "department": "CS",
                "credits": 4,
                "math_intensity": 0.7,
                "humanities_intensity": 0.2,
                "career_paths": ["software_engineer", "data_scientist"],
            },
            {
                "id": "course-phil-101",
                "name": "Introduction to Philosophy",
                "description": "Study of logic, ethics, and metaphysics",
                "department": "PHIL",
                "credits": 3,
                "math_intensity": 0.2,
                "humanities_intensity": 0.95,
                "career_paths": ["philosopher", "writer"],
            },
        ]

    @pytest.fixture
    def mock_cognee_response(self) -> Dict[str, Any]:
        """Create deterministic mock Cognee API response."""
        return {
            "success": True,
            "node_id": "test-node-id",
            "timestamp": "2024-01-01T00:00:00Z",
            "embedding_id": "test-embedding-id",
        }

    @pytest_asyncio.fixture
    async def adapter(self):
        """Create CogneeAdapter with mocked HTTP client."""
        pytest.importorskip("src.integrations.cognee_adapter", reason="Cognee adapter not available")

        from src.integrations.cognee_adapter import CogneeAdapter

        adapter = CogneeAdapter(
            api_url="http://test-cognee:8000",
            api_key="test-key",
            dataset_name="test_dataset",
        )

        # Mock the HTTP client
        mock_client = AsyncMock()
        adapter._http_client = mock_client

        yield adapter

        await adapter.close()

    def test_node_id_determinism(self, sample_courses):
        """Same course ID must generate same node ID.

        HARD CONSTRAINT: _generate_node_id() must produce identical
        UUIDs for identical (entity_type, unique_key) inputs.
        """
        from src.integrations.cognee_adapter import CogneeAdapter

        adapter = CogneeAdapter()

        # Generate node IDs for same course multiple times
        node_ids = []
        for _ in range(10):
            node_id = adapter._generate_node_id("Course", sample_courses[0]["id"])
            node_ids.append(node_id)

        # All must be identical
        first_id = node_ids[0]
        for i, nid in enumerate(node_ids[1:], 1):
            assert nid == first_id, (
                f"Node ID changed at iteration {i+1}:\n"
                f"Expected: {first_id}\n"
                f"Got: {nid}"
            )

    def test_node_id_different_types(self, sample_courses):
        """Different entity types must produce different node IDs for same key."""
        from src.integrations.cognee_adapter import CogneeAdapter

        adapter = CogneeAdapter()
        course_id = sample_courses[0]["id"]

        node_id_course = adapter._generate_node_id("Course", course_id)
        node_id_user = adapter._generate_node_id("User", course_id)
        node_id_doc = adapter._generate_node_id("Document", course_id)

        # All should be different
        assert node_id_course != node_id_user, "Course and User should have different IDs"
        assert node_id_course != node_id_doc, "Course and Document should have different IDs"
        assert node_id_user != node_id_doc, "User and Document should have different IDs"

    def test_content_hash_determinism(self):
        """Same content must produce same hash.

        HARD CONSTRAINT: _compute_content_hash() must produce identical
        hashes for identical content strings.
        """
        from src.integrations.cognee_adapter import CogneeAdapter

        adapter = CogneeAdapter()
        content = "Test course content for hashing"

        # Compute hash multiple times
        hashes = []
        for _ in range(10):
            h = adapter._compute_content_hash(content)
            hashes.append(h)

        # All must be identical
        first_hash = hashes[0]
        for i, h in enumerate(hashes[1:], 1):
            assert h == first_hash, (
                f"Hash changed at iteration {i+1}:\n"
                f"Expected: {first_hash}\n"
                f"Got: {h}"
            )

    def test_content_hash_different_content(self):
        """Different content must produce different hashes."""
        from src.integrations.cognee_adapter import CogneeAdapter

        adapter = CogneeAdapter()

        contents = [
            "Content A",
            "Content B",
            "Content A ",  # Trailing space
            " content A",  # Leading space
            "Content a",   # Different case
        ]

        hashes = [adapter._compute_content_hash(c) for c in contents]

        # All should be unique
        assert len(set(hashes)) == len(hashes), (
            f"Expected unique hashes, got duplicates:\n"
            f"Contents: {contents}\n"
            f"Hashes: {hashes}"
        )

    @pytest.mark.parametrize("run_count", [3, 5, 10])
    async def test_ingestion_idempotency(self, adapter, sample_courses, mock_cognee_response, run_count):
        """Ingesting same data multiple times must produce same node IDs.

        Runs ingestion {run_count} times and verifies identical node IDs.
        """
        from src.integrations.directus_neo4j_bridge import Course

        # Create Course objects
        courses = [
            Course(
                id=c["id"],
                name=c["name"],
                description=c["description"],
                department=c["department"],
                credits=c["credits"],
                math_intensity=c["math_intensity"],
                humanities_intensity=c["humanities_intensity"],
                career_paths=c["career_paths"],
            )
            for c in sample_courses
        ]

        # Run ingestion multiple times
        all_results = []
        for _ in range(run_count):
            # Reset mock for each run
            adapter._http_client.request = AsyncMock(return_value=MagicMock(
                json=lambda: mock_cognee_response,
                raise_for_status=lambda: None,
            ))

            result = await adapter.ingest_course_data(courses)
            all_results.append(result.node_ids.copy())

        # All runs must produce identical node ID lists
        first_result = all_results[0]
        for i, result in enumerate(all_results[1:], 1):
            assert result == first_result, (
                f"Run {i+1} produced different node IDs:\n"
                f"Expected: {first_result}\n"
                f"Got: {result}"
            )


class TestCogneeQueryDeterminism:
    """Test that queries produce deterministic results."""

    @pytest_asyncio.fixture
    async def adapter(self):
        """Create CogneeAdapter with mocked HTTP client."""
        from src.integrations.cognee_adapter import CogneeAdapter

        adapter = CogneeAdapter(
            api_url="http://test-cognee:8000",
            api_key="test-key",
            dataset_name="test_dataset",
        )

        mock_client = AsyncMock()
        adapter._http_client = mock_client

        yield adapter

        await adapter.close()

    @pytest.mark.parametrize("run_count", [5, 10])
    async def test_search_query_determinism(self, adapter, run_count):
        """Same search query must return same results.

        HARD CONSTRAINT: search_similar() must return identical results
        for identical queries across multiple runs.
        """
        # Create deterministic mock response
        mock_results = {
            "results": [
                {
                    "node_id": "node-1",
                    "content": "Mathematics course content",
                    "score": 0.95,
                    "metadata": {"course_id": "math-101"},
                    "relationships": [],
                },
                {
                    "node_id": "node-2",
                    "content": "Advanced calculus",
                    "score": 0.87,
                    "metadata": {"course_id": "math-201"},
                    "relationships": [],
                },
            ]
        }

        adapter._http_client.request = AsyncMock(return_value=MagicMock(
            json=lambda: mock_results,
            raise_for_status=lambda: None,
        ))

        query = "machine learning mathematics"

        # Run search multiple times
        all_results = []
        for _ in range(run_count):
            results = await adapter.search_similar(query, top_k=10)
            # Serialize for comparison (SearchResult objects)
            serialized = [
                {
                    "node_id": r.node_id,
                    "content": r.content,
                    "score": r.score,
                    "metadata": r.metadata,
                }
                for r in results
            ]
            all_results.append(json.dumps(serialized, sort_keys=True))

        # All must be identical
        first_result = all_results[0]
        for i, result in enumerate(all_results[1:], 1):
            assert result == first_result, (
                f"Run {i+1} produced different search results:\n"
                f"Expected: {first_result}\n"
                f"Got: {result}"
            )

    async def test_search_with_filters_determinism(self, adapter):
        """Search with filters must be deterministic."""
        mock_results = {
            "results": [
                {
                    "node_id": "node-cs-1",
                    "content": "Computer Science 101",
                    "score": 0.92,
                    "metadata": {"department": "CS"},
                    "relationships": [],
                }
            ]
        }

        adapter._http_client.request = AsyncMock(return_value=MagicMock(
            json=lambda: mock_results,
            raise_for_status=lambda: None,
        ))

        query = "programming"
        filters = {"node_type": "Course", "department": "CS"}

        # Run multiple times
        results_hashes = []
        for _ in range(5):
            results = await adapter.search_similar(query, filters=filters, top_k=5)
            # Hash the results
            result_str = json.dumps([
                {"node_id": r.node_id, "score": r.score}
                for r in results
            ], sort_keys=True)
            results_hashes.append(hashlib.sha256(result_str.encode()).hexdigest())

        # All hashes must be identical
        first_hash = results_hashes[0]
        for i, h in enumerate(results_hashes[1:], 1):
            assert h == first_hash, f"Run {i+1} produced different results hash"


class TestCogneeSanitizationDeterminism:
    """Test that input sanitization is deterministic."""

    @pytest.fixture
    def sanitizer(self):
        """Create InputSanitizer instance."""
        from src.integrations.cognee_adapter import InputSanitizer
        return InputSanitizer()

    def test_sanitize_string_determinism(self, sanitizer):
        """Same string must produce same sanitized output."""
        test_strings = [
            "Normal string",
            "String with \"quotes\"",
            "String with \\ backslash",
            "String with 'single' quotes",
            "Very long string " * 100,
        ]

        for test_str in test_strings:
            results = [sanitizer.sanitize_string(test_str) for _ in range(10)]
            first = results[0]
            for i, result in enumerate(results[1:], 1):
                assert result == first, (
                    f"Sanitization changed at iteration {i+1}:\n"
                    f"Input: {test_str[:50]}...\n"
                    f"Expected: {first}\n"
                    f"Got: {result}"
                )

    def test_sanitize_identifier_determinism(self, sanitizer):
        """Same identifier must produce same sanitized output."""
        test_ids = [
            "valid_id",
            "123starts_with_number",
            "with-dashes",
            "with spaces",
            "special!@#chars",
        ]

        for test_id in test_ids:
            results = [sanitizer.sanitize_identifier(test_id) for _ in range(10)]
            first = results[0]
            for i, result in enumerate(results[1:], 1):
                assert result == first, (
                    f"Identifier sanitization changed at iteration {i+1}:\n"
                    f"Input: {test_id}\n"
                    f"Expected: {first}\n"
                    f"Got: {result}"
                )

    def test_sanitize_metadata_determinism(self, sanitizer):
        """Same metadata must produce same sanitized output."""
        metadata = {
            "course_id": "course-123",
            "department": "Computer Science",
            "credits": 4,
            "tags": ["math", "programming", "advanced"],
            "active": True,
            "score": 3.14159,
        }

        results = [sanitizer.sanitize_metadata(metadata) for _ in range(10)]
        first = results[0]
        for i, result in enumerate(results[1:], 1):
            assert result == first, (
                f"Metadata sanitization changed at iteration {i+1}:\n"
                f"Expected: {first}\n"
                f"Got: {result}"
            )


class TestCogneeGraphWriteIdempotency:
    """Test graph write idempotency - same write → same state."""

    @pytest_asyncio.fixture
    async def adapter(self):
        """Create CogneeAdapter with mocked HTTP client."""
        from src.integrations.cognee_adapter import CogneeAdapter

        adapter = CogneeAdapter(
            api_url="http://test-cognee:8000",
            api_key="test-key",
            dataset_name="test_dataset",
        )

        mock_client = AsyncMock()
        adapter._http_client = mock_client

        yield adapter

        await adapter.close()

    async def test_user_interaction_idempotency(self, adapter):
        """Ingesting same user interaction twice must produce same node IDs."""
        from src.integrations.cognee_adapter import UserInteraction

        interactions = [
            UserInteraction(
                user_id="user-123",
                action="viewed",
                entity_id="course-math-101",
                entity_type="Course",
                timestamp="2024-01-01T12:00:00Z",
                metadata={"session_id": "sess-456"},
            )
        ]

        mock_response = {"success": True, "timestamp": "2024-01-01T00:00:00Z"}
        adapter._http_client.request = AsyncMock(return_value=MagicMock(
            json=lambda: mock_response,
            raise_for_status=lambda: None,
        ))

        # Run twice
        result1 = await adapter.ingest_user_interactions(interactions)
        result2 = await adapter.ingest_user_interactions(interactions)

        # Node IDs must be identical
        assert result1.node_ids == result2.node_ids, (
            f"Node IDs differ between runs:\n"
            f"Run 1: {result1.node_ids}\n"
            f"Run 2: {result2.node_ids}"
        )


class TestCogneeEmbeddingConsistency:
    """Test embedding consistency across runs."""

    def test_embedding_payload_determinism(self):
        """Same content must produce same embedding payload."""
        from src.integrations.cognee_adapter import CogneeAdapter, InputSanitizer

        adapter = CogneeAdapter()
        sanitizer = InputSanitizer()

        course_data = {
            "id": "course-test-001",
            "name": "Test Course",
            "description": "Test description for embedding",
            "department": "TEST",
        }

        # Build payload multiple times
        payloads = []
        for _ in range(5):
            safe_name = sanitizer.sanitize_string(course_data["name"])
            safe_description = sanitizer.sanitize_string(course_data["description"])
            content = f"{safe_name}. {safe_description}"
            content_hash = adapter._compute_content_hash(content)

            payload = {
                "data": content,
                "node_id": adapter._generate_node_id("Course", course_data["id"]),
                "content_hash": content_hash,
            }
            payloads.append(json.dumps(payload, sort_keys=True))

        # All must be identical
        first = payloads[0]
        for i, p in enumerate(payloads[1:], 1):
            assert p == first, (
                f"Payload changed at iteration {i+1}:\n"
                f"Expected: {first}\n"
                f"Got: {p}"
            )


class TestCogneeIntegrationDeterminism:
    """Integration-level determinism tests with hash comparison."""

    def test_full_ingestion_hash(self):
        """Full ingestion process must produce identical hashes."""
        from src.integrations.cognee_adapter import CogneeAdapter, InputSanitizer

        adapter = CogneeAdapter()
        sanitizer = InputSanitizer()

        courses = [
            {
                "id": f"course-{i:03d}",
                "name": f"Course {i}",
                "description": f"Description for course {i}",
                "department": "DEPT",
                "credits": 3,
                "math_intensity": 0.5,
                "humanities_intensity": 0.5,
                "career_paths": ["career_a", "career_b"],
            }
            for i in range(10)
        ]

        # Compute ingestion hashes multiple times
        hashes = []
        for _ in range(3):
            course_hashes = []
            for course in courses:
                node_id = adapter._generate_node_id("Course", course["id"])
                safe_name = sanitizer.sanitize_string(course["name"])
                safe_desc = sanitizer.sanitize_string(course["description"])
                content = f"{safe_name}. {safe_desc}"
                content_hash = adapter._compute_content_hash(content)

                course_data = {
                    "node_id": node_id,
                    "content_hash": content_hash,
                    "department": course["department"],
                }
                course_hashes.append(hashlib.sha256(
                    json.dumps(course_data, sort_keys=True).encode()
                ).hexdigest())

            # Combine all course hashes
            combined = hashlib.sha256(
                json.dumps(course_hashes, sort_keys=True).encode()
            ).hexdigest()
            hashes.append(combined)

        # All combined hashes must be identical
        first_hash = hashes[0]
        for i, h in enumerate(hashes[1:], 1):
            assert h == first_hash, (
                f"Hash mismatch at iteration {i+1}:\n"
                f"Expected: {first_hash}\n"
                f"Got: {h}"
            )
