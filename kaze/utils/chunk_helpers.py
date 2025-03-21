"""
Helper functions for working with code chunks.
Provides utilities for managing and displaying hierarchical code chunks.
"""

from typing import Dict, List, Optional, Any, Tuple
from rich import print
from rich.tree import Tree
from rich.syntax import Syntax
from rich.panel import Panel

from kaze.models.chunk import CodeChunk

def build_chunk_tree(chunks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Build a tree structure representing parent-child relationships between chunks.
    
    Args:
        chunks: List of chunk dictionaries
        
    Returns:
        Dictionary mapping parent chunk IDs to lists of child chunk IDs
    """
    # Create a dictionary to store the tree structure
    tree = {}
    
    # Group chunks by parent ID
    for chunk in chunks:
        parent_id = chunk.get("parent_id")
        
        if parent_id not in tree:
            tree[parent_id] = []
        
        tree[parent_id].append(chunk["id"])
    
    return tree

def print_chunk_tree(chunks: List[Dict[str, Any]], root_id: Optional[str] = None) -> None:
    """
    Print a tree representation of chunks to the console.
    
    Args:
        chunks: List of chunk dictionaries
        root_id: ID of the root chunk, or None for all top-level chunks
    """
    # Build a lookup table for chunks by ID
    chunk_by_id = {chunk["id"]: chunk for chunk in chunks}
    
    # Build the tree structure
    tree_struct = build_chunk_tree(chunks)
    
    # Create a rich Tree for display
    if root_id is None:
        # Start with all top-level chunks (those with no parent)
        root = Tree("🌲 Code Chunks")
        
        # Get top-level chunks (those with parent_id = None)
        if None in tree_struct:
            for chunk_id in tree_struct[None]:
                chunk = chunk_by_id[chunk_id]
                _add_chunk_to_tree(root, chunk, chunk_by_id, tree_struct)
    else:
        # Start with a specific chunk as the root
        if root_id not in chunk_by_id:
            print(f"[yellow]⚠️ Chunk with ID {root_id} not found[/yellow]")
            return
        
        root_chunk = chunk_by_id[root_id]
        root = Tree(f"🌲 {root_chunk['type']}:{root_chunk['name']}")
        
        # Add children of the root chunk
        if root_id in tree_struct:
            for chunk_id in tree_struct[root_id]:
                chunk = chunk_by_id[chunk_id]
                _add_chunk_to_tree(root, chunk, chunk_by_id, tree_struct)
    
    # Print the tree
    print(root)

def _add_chunk_to_tree(
    parent_node: Tree, 
    chunk: Dict[str, Any], 
    chunk_by_id: Dict[str, Dict[str, Any]], 
    tree_struct: Dict[str, List[str]]
) -> None:
    """
    Recursively add a chunk and its children to a rich Tree.
    
    Args:
        parent_node: The parent tree node
        chunk: The chunk to add
        chunk_by_id: Lookup table for chunks by ID
        tree_struct: Tree structure mapping parent IDs to child IDs
    """
    # Create a node for this chunk
    chunk_label = f"[cyan]{chunk['type']}[/cyan]:[yellow]{chunk['name']}[/yellow] (lines {chunk['start_line']}-{chunk['end_line']})"
    node = parent_node.add(chunk_label)
    
    # Recursively add children
    if chunk["id"] in tree_struct:
        for child_id in tree_struct[chunk["id"]]:
            child_chunk = chunk_by_id[child_id]
            _add_chunk_to_tree(node, child_chunk, chunk_by_id, tree_struct)

def display_chunk(chunk: Dict[str, Any], show_content: bool = True) -> None:
    """
    Display detailed information about a chunk.
    
    Args:
        chunk: The chunk dictionary
        show_content: Whether to show the content of the chunk
    """
    # Determine the file language for syntax highlighting
    file_extension = os.path.splitext(chunk["path"])[1].lower()
    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".md": "markdown",
        ".sh": "bash",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".go": "go",
        ".rb": "ruby",
        ".rs": "rust",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".sql": "sql",
        ".php": "php",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".xml": "xml",
    }
    language = language_map.get(file_extension, "text")
    
    # Create a header with chunk metadata
    header = (
        f"[cyan]{chunk['type']}[/cyan]:[yellow]{chunk['name']}[/yellow]\n"
        f"Path: [blue]{chunk['path']}[/blue]\n"
        f"Lines: {chunk['start_line']}-{chunk['end_line']} "
        f"({chunk['end_line'] - chunk['start_line'] + 1} lines)"
    )
    
    if chunk.get("parent_id"):
        header += f"\nParent: [green]{chunk['parent_id']}[/green]"
    
    print(Panel(header, title=f"Chunk: {chunk['id']}", expand=False))
    
    # Show content if requested
    if show_content and chunk.get("content"):
        print(Syntax(chunk["content"], language, line_numbers=True))
    
    # Show metadata if available
    if chunk.get("metadata") and chunk["metadata"] != {}:
        # Create a table for metadata
        table = Table(title="Metadata")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="yellow")
        
        for key, value in chunk["metadata"].items():
            table.add_row(str(key), str(value))
        
        print(table)

def filter_chunks_by_type(chunks: List[Dict[str, Any]], chunk_type: str) -> List[Dict[str, Any]]:
    """
    Filter chunks by their type.
    
    Args:
        chunks: List of chunk dictionaries
        chunk_type: Type to filter by (e.g., 'class', 'function')
        
    Returns:
        Filtered list of chunks
    """
    return [chunk for chunk in chunks if chunk["type"] == chunk_type]

def filter_chunks_by_name(chunks: List[Dict[str, Any]], name_pattern: str) -> List[Dict[str, Any]]:
    """
    Filter chunks by their name using a pattern.
    
    Args:
        chunks: List of chunk dictionaries
        name_pattern: Pattern to match against chunk names
        
    Returns:
        Filtered list of chunks
    """
    import re
    pattern = re.compile(name_pattern, re.IGNORECASE)
    return [chunk for chunk in chunks if pattern.search(chunk["name"])]

def get_chunk_ancestors(
    chunks: List[Dict[str, Any]], 
    chunk_id: str
) -> List[Dict[str, Any]]:
    """
    Get all ancestors (parents, grandparents, etc.) of a chunk.
    
    Args:
        chunks: List of chunk dictionaries
        chunk_id: ID of the chunk
        
    Returns:
        List of ancestor chunks, ordered from immediate parent to root
    """
    # Build a lookup table for chunks by ID
    chunk_by_id = {chunk["id"]: chunk for chunk in chunks}
    
    # Find the chunk
    if chunk_id not in chunk_by_id:
        return []
    
    # Get ancestors
    ancestors = []
    current = chunk_by_id[chunk_id]
    
    while current.get("parent_id") and current["parent_id"] in chunk_by_id:
        parent = chunk_by_id[current["parent_id"]]
        ancestors.append(parent)
        current = parent
    
    return ancestors

def get_chunk_descendants(
    chunks: List[Dict[str, Any]], 
    chunk_id: str
) -> List[Dict[str, Any]]:
    """
    Get all descendants (children, grandchildren, etc.) of a chunk.
    
    Args:
        chunks: List of chunk dictionaries
        chunk_id: ID of the chunk
        
    Returns:
        List of descendant chunks
    """
    # Build a lookup table for chunks by ID
    chunk_by_id = {chunk["id"]: chunk for chunk in chunks}
    
    # Build the tree structure
    tree_struct = build_chunk_tree(chunks)
    
    # Find the chunk
    if chunk_id not in chunk_by_id:
        return []
    
    # Get descendants
    descendants = []
    _collect_descendants(chunk_id, descendants, chunk_by_id, tree_struct)
    
    return descendants

def _collect_descendants(
    chunk_id: str, 
    descendants: List[Dict[str, Any]], 
    chunk_by_id: Dict[str, Dict[str, Any]], 
    tree_struct: Dict[str, List[str]]
) -> None:
    """
    Recursively collect descendants of a chunk.
    
    Args:
        chunk_id: ID of the chunk
        descendants: List to collect descendants into
        chunk_by_id: Lookup table for chunks by ID
        tree_struct: Tree structure mapping parent IDs to child IDs
    """
    if chunk_id in tree_struct:
        for child_id in tree_struct[chunk_id]:
            if child_id in chunk_by_id:
                child = chunk_by_id[child_id]
                descendants.append(child)
                _collect_descendants(child_id, descendants, chunk_by_id, tree_struct)
