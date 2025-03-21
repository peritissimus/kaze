"""
Base interface for language-specific parsers.
Defines the common interface that all language parsers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Import tree-sitter conditionally to handle environments where it's not available
try:
    from tree_sitter import Parser, Node

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logger.warning(
        "tree-sitter package not available. Falling back to regex-based parsing."
    )


class BaseLanguageParser(ABC):
    """Base class for language-specific parsers."""

    # Language ID (e.g., 'python', 'javascript')
    LANGUAGE_ID = ""

    # File extensions that this parser can handle
    FILE_EXTENSIONS = []

    def __init__(self):
        """Initialize the language parser."""
        self.parser = None

        # Initialize tree-sitter parser if available
        if TREE_SITTER_AVAILABLE:
            try:
                self.parser = Parser()
                logger.info(f"Initialized tree-sitter parser for {self.LANGUAGE_ID}")
            except Exception as e:
                logger.error(f"Error initializing tree-sitter parser: {e}")
                self.parser = None

    def extract_chunks(self, source_code: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract code chunks from source code.

        Args:
            source_code: The source code to parse
            file_path: Path to the source file

        Returns:
            List of chunk dictionaries with metadata
        """
        # Try tree-sitter parsing first if available
        if TREE_SITTER_AVAILABLE and self.parser is not None:
            try:
                return self._extract_chunks_tree_sitter(source_code, file_path)
            except Exception as e:
                logger.warning(
                    f"Tree-sitter parsing failed, falling back to regex: {e}"
                )

        # Fall back to regex-based parsing
        return self._extract_chunks_regex(source_code, file_path)

    def _extract_chunks_tree_sitter(
        self, source_code: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """Extract chunks using tree-sitter if available."""
        # This is just a stub that should be overridden by specific implementations
        # that have proper tree-sitter language support
        logger.warning(
            f"Tree-sitter extraction not implemented for {self.LANGUAGE_ID}, using regex fallback"
        )
        return self._extract_chunks_regex(source_code, file_path)

    @abstractmethod
    def _extract_chunks_regex(
        self, source_code: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """
        Extract code chunks using regex patterns as a fallback.

        This method should be implemented by each language parser to provide
        basic chunk extraction even without tree-sitter.

        Args:
            source_code: The source code to parse
            file_path: Path to the source file

        Returns:
            List of chunk dictionaries with metadata
        """
        pass

    @classmethod
    def can_handle_file(cls, file_path: str) -> bool:
        """
        Check if this parser can handle the given file.

        Args:
            file_path: Path to the file

        Returns:
            True if this parser can handle the file, False otherwise
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in cls.FILE_EXTENSIONS

    def _generate_chunk_id(
        self, file_path: str, chunk_type: str, name: str, line_number: int
    ) -> str:
        """Generate a consistent ID for a chunk."""
        return f"{file_path}:{chunk_type}:{name}:{line_number}"
