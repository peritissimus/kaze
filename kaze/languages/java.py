"""
Java language parser for Tree-sitter.
Implements Java-specific parsing rules for extracting code chunks.
"""

from typing import Dict, List, Any, Optional
from tree_sitter import Language, Tree, Node
import os
import re

from kaze.languages.base import BaseLanguageParser
from kaze.languages import register_language


class JavaParser(BaseLanguageParser):
    """Parser for Java language."""

    LANGUAGE_ID = "java"
    FILE_EXTENSIONS = [".java"]
    GRAMMAR_REPO = "https://github.com/tree-sitter/tree-sitter-java"

    def _get_language(self):
        """Get the Tree-sitter Language object for Java."""
        # Implementation would depend on how you've set up Tree-sitter
        # For now, return None as a placeholder
        return None

    def extract_chunks(self, source_code: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract code chunks from Java source code."""
        chunks = []

        # Parse the source code
        tree = self.parser.parse(bytes(source_code, "utf8"))

        # Process the syntax tree to extract chunks
        self._process_node(
            tree.root_node, source_code, file_path, chunks, parent_id=None
        )

        return chunks

    def _process_node(
        self,
        node: Node,
        source_code: str,
        file_path: str,
        chunks: List[Dict[str, Any]],
        parent_id: Optional[str] = None,
    ):
        """Process a node in the syntax tree to extract chunks."""
        # Java-specific node types
        if (
            node.type == "class_declaration"
            or node.type == "method_declaration"
            or node.type == "constructor_declaration"
            or node.type == "interface_declaration"
        ):
            # Extract node metadata
            node_type = self.get_node_type(node)
            node_name = self.get_node_name(node, source_code)

            # Calculate start and end positions
            start_point = node.start_point
            end_point = node.end_point

            # Extract the chunk text
            chunk_text = source_code[node.start_byte : node.end_byte]

            # Create a unique ID for the chunk
            chunk_id = f"{file_path}:{node_type}:{node_name}:{start_point[0]}"

            # Create the chunk dictionary
            chunk = {
                "id": chunk_id,
                "type": node_type,
                "name": node_name,
                "path": file_path,
                "start_line": start_point[0] + 1,  # 1-based line numbers
                "start_col": start_point[1],
                "end_line": end_point[0] + 1,
                "end_col": end_point[1],
                "parent_id": parent_id,
                "content": chunk_text,
            }

            # Add the chunk to the list
            chunks.append(chunk)

            # Process children with this node as the parent
            for child in node.children:
                self._process_node(
                    child, source_code, file_path, chunks, parent_id=chunk_id
                )
        else:
            # Process all children
            for child in node.children:
                self._process_node(
                    child, source_code, file_path, chunks, parent_id=parent_id
                )

    def get_node_type(self, node: Node) -> str:
        """Get the type of a Tree-sitter node for Java."""
        if node.type == "class_declaration":
            return "class"
        elif node.type == "method_declaration":
            return "method"
        elif node.type == "constructor_declaration":
            return "constructor"
        elif node.type == "interface_declaration":
            return "interface"
        return node.type

    def get_node_name(self, node: Node, source_code: str) -> str:
        """Get the name of a Tree-sitter node for Java."""
        if node.type == "class_declaration" or node.type == "interface_declaration":
            for child in node.children:
                if child.type == "identifier":
                    return source_code[child.start_byte : child.end_byte]
        elif node.type == "method_declaration":
            for child in node.children:
                if child.type == "identifier":
                    return source_code[child.start_byte : child.end_byte]
        elif node.type == "constructor_declaration":
            # Constructor is named after the class
            for child in node.children:
                if child.type == "identifier":
                    return source_code[child.start_byte : child.end_byte]

        return "unnamed"


# Register the Java parser
register_language(JavaParser.LANGUAGE_ID, JavaParser)
