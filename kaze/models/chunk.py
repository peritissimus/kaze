"""
Model for code chunks extracted using Tree-sitter.
Defines the data structure for code chunks and their relationships.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union


@dataclass
class CodeChunk:
    """
    Represents a code chunk extracted from a source file.
    A chunk is a logical unit of code (function, class, method, etc.)
    """

    # Unique identifier for the chunk
    id: str

    # Type of chunk (class, function, method, etc.)
    type: str

    # Name of the chunk (function name, class name, etc.)
    name: str

    # Path to the source file
    path: str

    # Line number where the chunk starts (1-based)
    start_line: int

    # Column number where the chunk starts
    start_col: int

    # Line number where the chunk ends (1-based)
    end_line: int

    # Column number where the chunk ends
    end_col: int

    # Content of the chunk
    content: str

    # ID of the parent chunk (e.g., class containing a method)
    # None for top-level chunks
    parent_id: Optional[str] = None

    # Additional metadata about the chunk
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Embedding vector for the chunk
    embedding: Optional[List[float]] = None

    @property
    def line_count(self) -> int:
        """Get the number of lines in the chunk."""
        return self.end_line - self.start_line + 1

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeChunk":
        """Create a CodeChunk instance from a dictionary."""
        return cls(
            id=data["id"],
            type=data["type"],
            name=data["name"],
            path=data["path"],
            start_line=data["start_line"],
            start_col=data["start_col"],
            end_line=data["end_line"],
            end_col=data["end_col"],
            content=data["content"],
            parent_id=data.get("parent_id"),
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the CodeChunk to a dictionary."""
        result = {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "path": self.path,
            "start_line": self.start_line,
            "start_col": self.start_col,
            "end_line": self.end_line,
            "end_col": self.end_col,
            "content": self.content,
        }

        if self.parent_id is not None:
            result["parent_id"] = self.parent_id

        if self.metadata:
            result["metadata"] = self.metadata

        if self.embedding is not None:
            result["embedding"] = self.embedding

        return result

    def get_qualified_name(self) -> str:
        """Get the fully qualified name of the chunk."""
        return f"{self.type}:{self.name}"

    def get_summary(self) -> str:
        """Get a summary of the chunk."""
        return (
            f"{self.get_qualified_name()} at {self.path}:"
            f"{self.start_line}-{self.end_line}"
        )
