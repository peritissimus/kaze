"""
TypeScript language parser for Tree-sitter.
Implements TypeScript-specific parsing rules for extracting code chunks.
"""

from typing import Dict, List, Any, Optional
from tree_sitter import Language, Tree, Node
import os
import re

from kaze.languages.base import BaseLanguageParser
from kaze.languages import register_language

class TypeScriptParser(BaseLanguageParser):
    """Parser for TypeScript language."""
    
    LANGUAGE_ID = "typescript"
    FILE_EXTENSIONS = [".ts", ".tsx"]
    GRAMMAR_REPO = "https://github.com/tree-sitter/tree-sitter-typescript"
    
    def _get_language(self):
        """Get the Tree-sitter Language object for TypeScript."""
        # Implementation would depend on how you've set up Tree-sitter
        # For now, return None as a placeholder
        return None
    
    def extract_chunks(self, source_code: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract code chunks from TypeScript source code."""
        chunks = []
        
        # Parse the source code
        tree = self.parser.parse(bytes(source_code, 'utf8'))
        
        # Process the syntax tree to extract chunks
        self._process_node(tree.root_node, source_code, file_path, chunks, parent_id=None)
        
        return chunks
    
    def _process_node(self, node: Node, source_code: str, file_path: str, 
                     chunks: List[Dict[str, Any]], parent_id: Optional[str] = None):
        """Process a node in the syntax tree to extract chunks."""
        # Similar to JavaScript but with TypeScript-specific node types
        # This would need to be adapted for TypeScript's specific syntax
        if (node.type == "class_declaration" or 
            node.type == "function_declaration" or 
            node.type == "method_definition" or 
            node.type == "arrow_function" or
            node.type == "interface_declaration"):
            
            # Extract node metadata
            node_type = self.get_node_type(node)
            node_name = self.get_node_name(node, source_code)
            
            # Skip anonymous functions if they don't have a name
            if node_name == "unnamed" and (node.type == "arrow_function" or node.type == "function"):
                # Process children even if we skip this node
                for child in node.children:
                    self._process_node(child, source_code, file_path, chunks, parent_id=parent_id)
                return
            
            # Calculate start and end positions
            start_point = node.start_point
            end_point = node.end_point
            
            # Extract the chunk text
            chunk_text = source_code[node.start_byte:node.end_byte]
            
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
                "content": chunk_text
            }
            
            # Add the chunk to the list
            chunks.append(chunk)
            
            # Process children with this node as the parent
            for child in node.children:
                self._process_node(child, source_code, file_path, chunks, parent_id=chunk_id)
        else:
            # Process all children
            for child in node.children:
                self._process_node(child, source_code, file_path, chunks, parent_id=parent_id)
    
    def get_node_type(self, node: Node) -> str:
        """Get the type of a Tree-sitter node for TypeScript."""
        if node.type == "class_declaration":
            return "class"
        elif node.type == "function_declaration":
            return "function"
        elif node.type == "method_definition":
            return "method"
        elif node.type == "arrow_function":
            return "arrow_function"
        elif node.type == "interface_declaration":
            return "interface"
        return node.type
    
    def get_node_name(self, node: Node, source_code: str) -> str:
        """Get the name of a Tree-sitter node for TypeScript."""
        # Similar to JavaScript but adapted for TypeScript's syntax
        if node.type == "class_declaration" or node.type == "function_declaration" or node.type == "interface_declaration":
            for child in node.children:
                if child.type == "type_identifier" or child.type == "identifier":
                    return source_code[child.start_byte:child.end_byte]
        elif node.type == "method_definition":
            for child in node.children:
                if child.type == "property_identifier":
                    return source_code[child.start_byte:child.end_byte]
        
        return "unnamed"

# Register the TypeScript parser
register_language(TypeScriptParser.LANGUAGE_ID, TypeScriptParser)
