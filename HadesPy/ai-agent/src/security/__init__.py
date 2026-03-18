"""Security validation and sanitization module.

Provides input validation, sanitization, and security hardening utilities
to prevent injection attacks and validate external inputs.

Usage:
    >>> from src.security import InputValidator
    >>> validator = InputValidator()
    >>> safe_id = validator.sanitize_cypher_identifier("user_input")
    >>> validator.validate_relationship_type("PREREQUISITE")
"""

import re
from typing import Any, List, Optional, Pattern, Set


class InputValidator:
    """Input validation and sanitization for security hardening.
    
    Provides methods to:
    - Sanitize Cypher identifiers (labels, property names)
    - Validate relationship types against allowlist
    - Sanitize SQL identifiers (table/column names)
    - Validate input length to prevent DoS
    - Validate node IDs
    
    Example:
        >>> validator = InputValidator()
        >>> # Sanitize Cypher identifier
        >>> safe = validator.sanitize_cypher_identifier("user-input")
        >>> # Validate relationship
        >>> if validator.validate_relationship_type(rel_type):
        ...     # Safe to use in query
    """
    
    # Allowed Cypher relationship types (allowlist)
    ALLOWED_CYPHER_RELATIONSHIPS: Set[str] = {
        'COMPLETED',
        'PREREQUISITE',
        'PREREQUISITE_FOR',
        'PREREQUISITE_OF',
        'SIMILAR_TO',
        'INTERACTED',
        'BELONGS_TO',
    }
    
    # Allowed SQL table/column names (allowlist)
    ALLOWED_SQL_TABLES: Set[str] = {
        'courses',
        'students',
        'courses_prerequisites',
        'course_embeddings',
        'recommendations',
    }
    
    ALLOWED_SQL_COLUMNS: Set[str] = {
        'id', 'name', 'description', 'department', 'credits',
        'math_intensity', 'humanities_intensity', 'career_paths',
        'embedding', 'status', 'created_at', 'updated_at',
        'course_id', 'prerequisite_id', 'student_id', 'preferences',
        'career_goal', 'user_id', 'item_id', 'score', 'reason',
    }
    
    # Maximum query length to prevent DoS
    MAX_QUERY_LENGTH: int = 10000
    
    # Maximum input length for various fields
    MAX_ID_LENGTH: int = 256
    MAX_NAME_LENGTH: int = 500
    MAX_DESCRIPTION_LENGTH: int = 5000
    MAX_CAREER_PATH_LENGTH: int = 100
    
    # Pattern for valid identifiers (alphanumeric + underscore, must start with letter)
    _VALID_IDENTIFIER_PATTERN: Pattern = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')
    
    # Pattern for valid UUIDs
    _UUID_PATTERN: Pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    # Pattern for valid node IDs (alphanumeric, dash, underscore)
    _NODE_ID_PATTERN: Pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
    
    # Dangerous Cypher keywords that should not appear in identifiers
    _DANGEROUS_CYPHER_KEYWORDS: Set[str] = {
        'MATCH', 'WHERE', 'RETURN', 'CREATE', 'DELETE', 'SET', 'REMOVE',
        'WITH', 'UNWIND', 'CALL', 'YIELD', 'LOAD', 'CSV', 'FROM', 'PERIODIC',
        'COMMIT', 'USING', 'INDEX', 'DROP', 'CONSTRAINT', 'ASSERT', 'IS',
        'UNIQUE', 'EXISTS', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AND',
        'OR', 'XOR', 'NOT', 'IN', 'STARTS', 'ENDS', 'CONTAINS', 'NULL',
        'TRUE', 'FALSE', 'AS', 'DISTINCT', 'ORDER', 'BY', 'ASC', 'DESC',
        'SKIP', 'LIMIT', 'ON', 'MERGE', 'OPTIONAL', 'DETACH',
    }
    
    # Dangerous SQL keywords
    _DANGEROUS_SQL_KEYWORDS: Set[str] = {
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE',
        'UNION', 'EXEC', 'EXECUTE', 'SCRIPT', 'SHUTDOWN', 'CREATE',
        'ALTER', 'TABLE', 'DATABASE', 'GRANT', 'REVOKE', 'DENY',
    }
    
    def __init__(
        self,
        max_query_length: Optional[int] = None,
        allowed_relationships: Optional[Set[str]] = None,
    ):
        """Initialize InputValidator.
        
        Args:
            max_query_length: Override default MAX_QUERY_LENGTH
            allowed_relationships: Override default ALLOWED_CYPHER_RELATIONSHIPS
        """
        self.max_query_length = max_query_length or self.MAX_QUERY_LENGTH
        self.allowed_relationships = allowed_relationships or self.ALLOWED_CYPHER_RELATIONSHIPS
    
    def sanitize_cypher_identifier(self, name: str) -> str:
        """Sanitize a Cypher identifier (label, property name, variable).
        
        Removes or escapes dangerous characters and validates against
        Cypher injection patterns.
        
        Args:
            name: The identifier to sanitize
            
        Returns:
            Sanitized identifier safe for use in Cypher queries
            
        Raises:
            ValueError: If the identifier contains dangerous patterns
            
        Example:
            >>> validator = InputValidator()
            >>> validator.sanitize_cypher_identifier("course-name")
            'course_name'
            >>> validator.sanitize_cypher_identifier("DROP TABLE")
            ValueError: Identifier contains dangerous keyword: DROP
        """
        if not name:
            return "_"
        
        # Check input length
        if len(name) > self.MAX_NAME_LENGTH:
            raise ValueError(
                f"Identifier too long: {len(name)} > {self.MAX_NAME_LENGTH}"
            )
        
        # Check for dangerous keywords (case-insensitive)
        upper_name = name.upper()
        for keyword in self._DANGEROUS_CYPHER_KEYWORDS:
            if keyword in upper_name.split():
                raise ValueError(f"Identifier contains dangerous keyword: {keyword}")
        
        # Replace dangerous characters with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'n' + sanitized
        
        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove trailing underscore
        sanitized = sanitized.rstrip('_')
        
        return sanitized or "_"
    
    def validate_relationship_type(self, rel_type: str) -> bool:
        """Validate a Cypher relationship type against allowlist.
        
        Args:
            rel_type: Relationship type to validate
            
        Returns:
            True if the relationship type is allowed
            
        Raises:
            ValueError: If the relationship type is not in the allowlist
            
        Example:
            >>> validator = InputValidator()
            >>> validator.validate_relationship_type("PREREQUISITE")
            True
            >>> validator.validate_relationship_type("DROP")
            ValueError: Relationship type not allowed: DROP
        """
        if not rel_type:
            raise ValueError("Relationship type cannot be empty")
        
        # Normalize: uppercase and remove surrounding colons if present
        normalized = rel_type.upper().strip(':')
        
        if normalized not in self.allowed_relationships:
            raise ValueError(
                f"Relationship type not allowed: {rel_type}. "
                f"Allowed types: {sorted(self.allowed_relationships)}"
            )
        
        return True
    
    def sanitize_sql_identifier(self, name: str) -> str:
        """Sanitize a SQL identifier (table or column name).
        
        Args:
            name: The identifier to sanitize
            
        Returns:
            Sanitized identifier safe for use in SQL queries
            
        Raises:
            ValueError: If the identifier contains dangerous patterns
            
        Example:
            >>> validator = InputValidator()
            >>> validator.sanitize_sql_identifier("course_name")
            'course_name'
        """
        if not name:
            raise ValueError("SQL identifier cannot be empty")
        
        # Check input length
        if len(name) > self.MAX_NAME_LENGTH:
            raise ValueError(
                f"Identifier too long: {len(name)} > {self.MAX_NAME_LENGTH}"
            )
        
        # Check for dangerous keywords
        upper_name = name.upper()
        for keyword in self._DANGEROUS_SQL_KEYWORDS:
            if keyword in upper_name.split():
                raise ValueError(f"SQL identifier contains dangerous keyword: {keyword}")
        
        # Replace dangerous characters
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'n' + sanitized
        
        return sanitized
    
    def validate_sql_table(self, table_name: str) -> bool:
        """Validate a SQL table name against allowlist.
        
        Args:
            table_name: Table name to validate
            
        Returns:
            True if the table name is allowed
            
        Raises:
            ValueError: If the table name is not in the allowlist
        """
        sanitized = self.sanitize_sql_identifier(table_name)
        
        if sanitized not in self.ALLOWED_SQL_TABLES:
            raise ValueError(
                f"Table not allowed: {table_name}. "
                f"Allowed tables: {sorted(self.ALLOWED_SQL_TABLES)}"
            )
        
        return True
    
    def validate_sql_column(self, column_name: str) -> bool:
        """Validate a SQL column name against allowlist.
        
        Args:
            column_name: Column name to validate
            
        Returns:
            True if the column name is allowed
            
        Raises:
            ValueError: If the column name is not in the allowlist
        """
        sanitized = self.sanitize_sql_identifier(column_name)
        
        if sanitized not in self.ALLOWED_SQL_COLUMNS:
            raise ValueError(
                f"Column not allowed: {column_name}. "
                f"Allowed columns: {sorted(self.ALLOWED_SQL_COLUMNS)}"
            )
        
        return True
    
    def validate_input_length(self, data: Any, max_length: Optional[int] = None) -> bool:
        """Validate input length to prevent DoS attacks.
        
        Args:
            data: Input data to validate (string, list, dict, bytes)
            max_length: Maximum allowed length (default: MAX_QUERY_LENGTH)
            
        Returns:
            True if input length is within limits
            
        Raises:
            ValueError: If input exceeds maximum length
        """
        max_len = max_length or self.max_query_length
        
        if isinstance(data, str):
            length = len(data)
        elif isinstance(data, (list, tuple)):
            length = len(data)
        elif isinstance(data, dict):
            length = len(str(data))
        elif isinstance(data, bytes):
            length = len(data)
        elif data is None:
            return True
        else:
            length = len(str(data))
        
        if length > max_len:
            raise ValueError(
                f"Input exceeds maximum length: {length} > {max_len}"
            )
        
        return True
    
    def validate_node_id(self, node_id: str) -> bool:
        """Validate a node ID format.
        
        Args:
            node_id: Node ID to validate
            
        Returns:
            True if the node ID is valid
            
        Raises:
            ValueError: If the node ID format is invalid
        """
        if not node_id:
            raise ValueError("Node ID cannot be empty")
        
        if len(node_id) > self.MAX_ID_LENGTH:
            raise ValueError(
                f"Node ID too long: {len(node_id)} > {self.MAX_ID_LENGTH}"
            )
        
        # Check for valid characters
        if not self._NODE_ID_PATTERN.match(node_id):
            raise ValueError(
                f"Invalid node ID format: {node_id}. "
                "Only alphanumeric characters, dashes, and underscores are allowed."
            )
        
        return True
    
    def validate_uuid(self, uuid_str: str) -> bool:
        """Validate a UUID string format.
        
        Args:
            uuid_str: UUID string to validate
            
        Returns:
            True if the UUID format is valid
        """
        if not uuid_str:
            raise ValueError("UUID cannot be empty")
        
        if not self._UUID_PATTERN.match(uuid_str):
            raise ValueError(f"Invalid UUID format: {uuid_str}")
        
        return True
    
    def validate_vector_dimension(
        self,
        vector: List[float],
        expected_dimension: int,
    ) -> bool:
        """Validate vector dimension.
        
        Args:
            vector: Vector to validate
            expected_dimension: Expected dimension size
            
        Returns:
            True if the vector dimension matches
            
        Raises:
            ValueError: If dimensions don't match
        """
        actual_dim = len(vector)
        
        if actual_dim != expected_dimension:
            raise ValueError(
                f"Vector dimension mismatch: {actual_dim} != {expected_dimension}"
            )
        
        return True
    
    def sanitize_cypher_relationship_pattern(self, pattern: str) -> str:
        """Sanitize a Cypher relationship pattern for use in queries.
        
        This is used when dynamically building relationship type patterns
        like (a)-[:TYPE1|TYPE2]->(b).
        
        Args:
            pattern: Relationship pattern string
            
        Returns:
            Sanitized pattern with only allowed relationship types
        """
        if not pattern:
            return ""
        
        # Split by pipe (union of relationship types)
        types = pattern.split('|')
        
        # Validate each type
        valid_types = []
        for rel_type in types:
            rel_type = rel_type.strip().upper()
            try:
                if self.validate_relationship_type(rel_type):
                    valid_types.append(rel_type)
            except ValueError:
                # Skip invalid types
                continue
        
        return '|'.join(valid_types) if valid_types else ""


# Convenience function for quick validation
def get_validator() -> InputValidator:
    """Get a default InputValidator instance."""
    return InputValidator()
