"""Vector module for LanceDB course embeddings."""

from src.vector.course_store import (
    CourseVectorStore,
    CourseVectorRecord,
    CourseSearchResult,
)

__all__ = [
    "CourseVectorStore",
    "CourseVectorRecord",
    "CourseSearchResult",
]
