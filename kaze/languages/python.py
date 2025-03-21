"""
Python language parser for code chunk extraction.
Implements Python-specific parsing rules for extracting code chunks.
"""

from typing import Dict, List, Any, Tuple
import re
import logging

from kaze.languages.base import BaseLanguageParser, TREE_SITTER_AVAILABLE
from kaze.languages import register_language

# Configure logging
logger = logging.getLogger(__name__)

# Import tree-sitter types conditionally
if TREE_SITTER_AVAILABLE:
    pass


class PythonParser(BaseLanguageParser):
    """Parser for Python language."""

    LANGUAGE_ID = "python"
    FILE_EXTENSIONS = [".py"]

    # Regular expressions for Python code chunks
    CLASS_PATTERN = r"(?:@\w+(?:\(.*?\))?\s*\n)*class\s+(\w+)(?:\s*\(\s*.*?\s*\))?\s*:"
    FUNCTION_PATTERN = (
        r"(?:@\w+(?:\(.*?\))?\s*\n)*def\s+(\w+)\s*\(.*?\)\s*(?:->.*?)?\s*:"
    )
    DECORATOR_PATTERN = r"@(\w+)(?:\(.*?\))?"

    # Indentation utils
    @staticmethod
    def get_indentation(line: str) -> int:
        """Get the indentation level of a line."""
        return len(line) - len(line.lstrip())

    @staticmethod
    def get_line_indent(source_code: str, line_number: int) -> int:
        """Get the indentation of a specific line."""
        lines = source_code.splitlines()
        if 0 <= line_number < len(lines):
            return PythonParser.get_indentation(lines[line_number])
        return 0

    def _extract_chunk_content(
        self, source_code: str, start_line: int
    ) -> Tuple[str, int]:
        """
        Extract a chunk's content based on indentation.

        Args:
            source_code: The source code
            start_line: The line number where the chunk starts

        Returns:
            Tuple of (chunk content, end line number)
        """
        lines = source_code.splitlines()
        if start_line >= len(lines):
            return "", start_line

        # Get the indentation of the chunk definition
        definition_indent = self.get_indentation(lines[start_line])

        # Start with the definition line
        chunk_lines = [lines[start_line]]
        end_line = start_line

        # Find the first non-empty line after the definition to get the chunk's indentation
        chunk_indent = None
        for i in range(start_line + 1, len(lines)):
            if lines[i].strip():  # Non-empty line
                current_indent = self.get_indentation(lines[i])
                if current_indent <= definition_indent:
                    # This line has less indentation than the definition, so it's outside the chunk
                    break
                if chunk_indent is None:
                    chunk_indent = current_indent
                chunk_lines.append(lines[i])
                end_line = i
            else:
                # Include blank lines
                chunk_lines.append(lines[i])
                end_line = i

        return "\n".join(chunk_lines), end_line

    def _get_decorators_from_lines(
        self, source_code: str, start_line: int
    ) -> List[str]:
        """Extract decorators from lines preceding a chunk."""
        lines = source_code.splitlines()
        decorators = []

        # Look at lines before the class/function definition
        line_idx = start_line - 1
        while line_idx >= 0:
            line = lines[line_idx].strip()
            if line.startswith("@"):
                decorators.insert(0, line)
                line_idx -= 1
            else:
                # Stop when we hit a non-decorator line
                break

        return decorators

    def _extract_chunks_regex(
        self, source_code: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """
        Extract code chunks using regex patterns.

        Args:
            source_code: The source code to parse
            file_path: Path to the source file

        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        lines = source_code.splitlines()

        # Keep track of classes to determine if functions are methods
        class_stack = []

        # First pass: identify all classes and functions
        for i, line in enumerate(lines):
            # Check for class definitions
            class_match = re.search(self.CLASS_PATTERN, line)
            if class_match:
                class_name = class_match.group(1)
                content, end_line = self._extract_chunk_content(source_code, i)
                decorators = self._get_decorators_from_lines(source_code, i)

                # Add indentation level to track nesting
                indent_level = self.get_indentation(line)

                # Remove any classes from the stack that have less indentation
                while class_stack and class_stack[-1]["indent"] >= indent_level:
                    class_stack.pop()

                # Create the chunk
                parent_id = class_stack[-1]["id"] if class_stack else None

                chunk_id = self._generate_chunk_id(file_path, "class", class_name, i)

                chunk = {
                    "id": chunk_id,
                    "type": "class",
                    "name": class_name,
                    "path": file_path,
                    "start_line": i + 1,  # 1-based line numbers
                    "start_col": 0,  # Regex doesn't give precise column info
                    "end_line": end_line + 1,
                    "end_col": len(lines[end_line]) if end_line < len(lines) else 0,
                    "parent_id": parent_id,
                    "content": content,
                    "decorators": decorators,
                }

                chunks.append(chunk)

                # Add to class stack
                class_stack.append(
                    {"id": chunk_id, "name": class_name, "indent": indent_level}
                )

            # Check for function definitions
            function_match = re.search(self.FUNCTION_PATTERN, line)
            if function_match:
                function_name = function_match.group(1)
                content, end_line = self._extract_chunk_content(source_code, i)
                decorators = self._get_decorators_from_lines(source_code, i)

                # Determine if this is a method
                indent_level = self.get_indentation(line)
                parent_id = None
                chunk_type = "function"

                # Check if this function is inside a class (making it a method)
                for class_info in reversed(class_stack):
                    if class_info["indent"] < indent_level:
                        parent_id = class_info["id"]
                        chunk_type = "method"
                        break

                chunk = {
                    "id": self._generate_chunk_id(
                        file_path, chunk_type, function_name, i
                    ),
                    "type": chunk_type,
                    "name": function_name,
                    "path": file_path,
                    "start_line": i + 1,  # 1-based line numbers
                    "start_col": 0,  # Regex doesn't give precise column info
                    "end_line": end_line + 1,
                    "end_col": len(lines[end_line]) if end_line < len(lines) else 0,
                    "parent_id": parent_id,
                    "content": content,
                    "decorators": decorators,
                }

                chunks.append(chunk)

        return chunks

    def _extract_chunks_tree_sitter(
        self, source_code: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """
        Extract code chunks using tree-sitter.

        This is only used when tree-sitter is available and properly configured.

        Args:
            source_code: The source code to parse
            file_path: Path to the source file

        Returns:
            List of chunk dictionaries with metadata
        """
        logger.warning(
            "Tree-sitter support is not fully implemented. Using regex fallback."
        )
        return self._extract_chunks_regex(source_code, file_path)


# Register the Python parser
register_language(PythonParser.LANGUAGE_ID, PythonParser)
