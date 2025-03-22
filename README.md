# Kaze

Kaze is a unified tool for creating and querying vector embeddings of your project files. It helps you semantically search through your codebase to find relevant files and code chunks based on natural language queries.

## Features

- **File Embeddings**: Create embeddings for entire files in your project
- **Code Chunk Extraction**: Extract and embed individual code chunks (functions, classes, methods) for more precise searching
- **Semantic Search**: Query your codebase using natural language
- **Tree-sitter Integration**: Language-aware code parsing (when Tree-sitter is available)
- **Hierarchical Chunks**: Understand parent-child relationships between code elements
- **Flexible Output**: Human-readable or JSON output for integration with other tools

## Installation

```bash
# Install from PyPI
pip install kaze

# Or install with development dependencies
pip install kaze[dev]
```

## Usage

### Creating File Embeddings

```bash
# Create embeddings for the current directory
kaze create

# Create embeddings with custom settings
kaze create --dir /path/to/project --model text-embedding-3-small --size 200 --batch 30 --collection my-project
```

Options:
- `-d, --dir`: Project directory (default: current directory)
- `-o, --output`: Output directory (default: `.kaze` in project directory)
- `-m, --model`: Embedding model to use (default: text-embedding-3-small)
- `-s, --size`: Maximum file size in KB (default: 100)
- `-b, --batch`: Batch size for processing (default: 20)
- `-c, --collection`: Collection name (default: files)
- `-f, --force`: Force recreation of embeddings database
- `--include`: Additional files to include (glob pattern)
- `--exclude`: Additional files to exclude (glob pattern)
- `--verify`: Verify embedding model is available

### Querying File Embeddings

```bash
# Search for files related to a query
kaze query --query "database connection function"

# Get only the best match with content
kaze query --query "file handling utilities" --best --show-content

# Get matching files with context
kaze query --query "error handling" --context 10
```

Options:
- `-d, --dir`: Project directory (default: current directory)
- `-o, --output`: Output directory (default: `.kaze` in project directory)
- `-q, --query`: Text to search for (required)
- `-n, --limit`: Maximum number of results (default: 10)
- `-t, --threshold`: Similarity threshold (0.0-1.0) (default: 0.2)
- `-c, --collection`: Collection to search in (default: files)
- `--show-content`: Show file content in results
- `--human`: Display human-readable output (default: True)
- `--best`: Only show the single best matching result
- `--context`: Number of lines of context to show around the matching part

### Working with Code Chunks

#### Creating Chunk Embeddings

```bash
# Create code chunk embeddings
kaze chunks create

# Create chunks with custom settings
kaze chunks create --dir /path/to/project --model text-embedding-3-small --collection code-chunks
```

Options:
- Same options as `kaze create`, plus:
- `--sequential`: Process files sequentially (recommended to avoid database locks) (default: True)

#### Querying Chunks

```bash
# Search for code chunks related to a query
kaze chunks query --query "database connection retry logic"

# Filter by chunk type
kaze chunks query --query "parse file content" --type function --show-content
```

Options:
- Same options as `kaze query`, plus:
- `-y, --type`: Filter by chunk type (class, function, method, etc.)

#### Listing Chunks

```bash
# List all chunks
kaze chunks list

# List chunks in a specific file
kaze chunks list --file "core/file_utils.py"

# List chunks of a specific type
kaze chunks list --type class

# Show chunks as a tree
kaze chunks list --tree
```

#### Viewing Chunk Details

```bash
# Show details of a specific chunk
kaze chunks show --id "path/to/file.py:function:get_file_list:123"

# Show chunk with its children
kaze chunks show --id "path/to/file.py:class:Parser:45" --show-children

# Show chunk with its parent hierarchy
kaze chunks show --id "path/to/file.py:method:parse:78" --show-ancestors
```

#### Chunk Statistics

```bash
# Show statistics about chunks
kaze chunks stats
```

### Getting Database Info

```bash
# Show information about the embeddings database
kaze info
```

Options:
- `-d, --dir`: Project directory (default: current directory)
- `-o, --output`: Output directory (default: `.kaze` in project directory)

## Advanced Features

### Language Support

Kaze currently supports code chunk extraction for:
- Python
- More languages coming soon

When Tree-sitter is available, Kaze can provide more accurate code chunk extraction.

### Database Structure

Kaze uses SQLite with the following optimizations:
- Write-Ahead Logging for better concurrency
- Connection pooling to reduce locking issues
- Retry mechanisms for database operations

## Requirements

- Python 3.6+
- llm
- click
- rich
- tiktoken
- sqlite-utils
- tree-sitter (optional, for improved code parsing)

## Development

This project uses conventional commits for versioning. You can update the version with the included script:

```bash
python scripts/version.py
```

To create a release:

```bash
python scripts/release.py
```

## License

[MIT](LICENSE)
