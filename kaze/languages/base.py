"""
Base interface for language-specific parsers.
Defines the common interface that all language parsers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from tree_sitter import Language, Parser, Tree, Node
import os

class BaseLanguageParser(ABC):
    """Base class for language-specific parsers."""
    
    # Language ID (e.g., 'python', 'javascript')
    LANGUAGE_ID = ""
    
    # File extensions that this parser can handle
    FILE_EXTENSIONS = []
    
    # Tree-sitter grammar repository URL
    GRAMMAR_REPO = ""
    
    def __init__(self):
        """Initialize the language parser."""
        self.parser = None
        self.language = None
        self._initialize_parser()
    
    def _initialize_parser(self):
        """Initialize the Tree-sitter parser for this language."""
        # This would be implemented based on Tree-sitter's requirements
        # For now, this is a placeholder
        self.parser = Parser()
        # self.language = self._get_language()
        # self.parser.set_language(self.language)
    
    @abstractmethod
    def _get_language(self) -> Language:
        """Get the Tree-sitter Language object for this language."""
        pass
    
    @abstractmethod
    def extract_chunks(self, source_code: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract code chunks from source code.
        
        Args:
            source_code: The source code to parse
            file_path: Path to the source file
            
        Returns:
            List of chunk dictionaries with metadata
        """
        pass
    
    @abstractmethod
    def get_node_type(self, node: Node) -> str:
        """
        Get the type of a Tree-sitter node.
        
        Args:
            node: The Tree-sitter node
            
        Returns:
            Node type string (e.g., 'function', 'class', 'method')
        """
        pass
    
    @abstractmethod
    def get_node_name(self, node: Node, source_code: str) -> str:
        """
        Get the name of a Tree-sitter node.
        
        Args:
            node: The Tree-sitter node
            source_code: The source code
            
        Returns:
            Node name string
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
