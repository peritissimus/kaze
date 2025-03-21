"""
Tree-sitter integration utilities for code parsing and chunk extraction.
This module handles the parsing of source code files using Tree-sitter,
extracting hierarchical code chunks based on language syntax.
"""

from typing import Dict, List, Optional, Any
from rich import print

# Import tree-sitter conditionally to handle environments where it's not available
try:
    from tree_sitter import Language, Parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    print(
        "[yellow]⚠️ tree-sitter package not available. Falling back to regex-based parsing.[/yellow]"
    )

from kaze.languages import get_language_parser, get_supported_languages


def detect_language(file_path: str) -> Optional[str]:
    """
    Detect the programming language of a file based on its extension.

    Args:
        file_path: Path to the file

    Returns:
        Language ID string or None if the language is not supported
    """
    # Get all supported languages
    supported_languages = get_supported_languages()

    # Check each language parser to see if it can handle this file
    for language_id, parser_class in supported_languages.items():
        if parser_class.can_handle_file(file_path):
            return language_id

    return None


def extract_chunks_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract code chunks from a file.

    Args:
        file_path: Path to the file

    Returns:
        List of chunk dictionaries with metadata
    """
    try:
        # Detect the language
        language_id = detect_language(file_path)
        if not language_id:
            print(f"[yellow]⚠️ Unsupported language for file: {file_path}[/yellow]")
            return []

        # Get the language parser
        parser_class = get_language_parser(language_id)
        if not parser_class:
            print(f"[yellow]⚠️ No parser available for language: {language_id}[/yellow]")
            return []

        # Initialize the parser
        parser = parser_class()

        # Read the file
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source_code = f.read()

        # Extract chunks
        chunks = parser.extract_chunks(source_code, file_path)

        print(f"[green]✓ Extracted {len(chunks)} chunks from {file_path}[/green]")
        return chunks

    except Exception as e:
        print(f"[red]❌ Error extracting chunks from {file_path}: {e}[/red]")
        return []


def get_chunk_by_id(
    chunks: List[Dict[str, Any]], chunk_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get a chunk by its ID.

    Args:
        chunks: List of chunks
        chunk_id: ID of the chunk to find

    Returns:
        Chunk dictionary or None if not found
    """
    for chunk in chunks:
        if chunk["id"] == chunk_id:
            return chunk
    return None


def get_chunk_children(
    chunks: List[Dict[str, Any]], chunk_id: str
) -> List[Dict[str, Any]]:
    """
    Get all direct children of a chunk.

    Args:
        chunks: List of chunks
        chunk_id: ID of the parent chunk

    Returns:
        List of child chunks
    """
    return [chunk for chunk in chunks if chunk.get("parent_id") == chunk_id]


def get_chunk_tree(
    chunks: List[Dict[str, Any]], chunk_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a tree structure of chunks.

    Args:
        chunks: List of chunks
        chunk_id: ID of the root chunk, or None for the entire tree

    Returns:
        Tree structure of chunks
    """
    if chunk_id is None:
        # Get all top-level chunks (no parent)
        roots = [chunk for chunk in chunks if chunk.get("parent_id") is None]
        result = {"children": []}
        for root in roots:
            result["children"].append(get_chunk_tree(chunks, root["id"]))
        return result
    else:
        # Get the chunk and its children
        chunk = get_chunk_by_id(chunks, chunk_id)
        if not chunk:
            return {}

        result = chunk.copy()
        result["children"] = []

        children = get_chunk_children(chunks, chunk_id)
        for child in children:
            result["children"].append(get_chunk_tree(chunks, child["id"]))

        return result
