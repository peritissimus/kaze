# Kaze

Kaze is a unified tool for creating and querying vector embeddings of your project files. It helps you semantically search through your codebase to find relevant files and snippets based on natural language queries.


## Usage

### Creating Embeddings

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

### Querying Embeddings

```bash
# Search for files related to a query
kaze query --query "database connection function"

# Get only the best match with content
kaze query --query "file handling utilities" --best --show-content
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

### Getting Database Info

```bash
# Show information about the embeddings database
kaze info
```

Options:
- `-d, --dir`: Project directory (default: current directory)
- `-o, --output`: Output directory (default: `.kaze` in project directory)

## Requirements

- Python 3.6+
- llm
- click
- rich
- tiktoken
- sqlite-utils

## Development

This project uses conventional commits for versioning. You can update the version with the included script:

```bash
python scripts/version.py
```

## License

[MIT](LICENSE)
