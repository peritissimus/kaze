import llm
import os
import sqlite_utils
from rich import print
import tiktoken
import asyncio
import sqlite3
import contextlib
from functools import wraps

from kaze.core import treesitter_utils, db_utils

# Connection pool management
_connection_pool = {}


@contextlib.contextmanager
def get_db_connection(db_path, timeout=20.0):
    """Get a database connection with proper settings to reduce locking."""
    conn = sqlite3.connect(db_path, timeout=timeout)
    try:
        # Configure SQLite for better concurrency
        conn.execute(
            "PRAGMA journal_mode=WAL"
        )  # Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and speed
        conn.execute("PRAGMA busy_timeout=10000")  # 10 seconds busy timeout
        conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
        conn.execute("PRAGMA cache_size=-10000")  # Use larger cache (about 10MB)
        conn.execute("PRAGMA mmap_size=30000000")  # Memory map for faster access
        yield conn
    finally:
        conn.close()


def with_retry(max_retries=5, initial_delay=1.0, backoff_factor=2.0):
    """
    Decorator for retrying database operations with exponential backoff.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay

            for retry in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e):
                        print(
                            f"[yellow]⚠️ Database locked, retrying in {delay:.1f}s (attempt {retry+1}/{max_retries})[/yellow]"
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    else:
                        raise

            # If we've exhausted all retries
            print(f"[red]❌ Failed after {max_retries} retries[/red]")
            raise

        return wrapper

    return decorator


async def embed_file(file_path, model_name, db_path, collection_name):
    """Embed the content of a file using the Collection class approach"""
    try:
        # Calculate the file ID (relative path)
        file_id = os.path.relpath(file_path, os.getcwd())

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Skip empty files
        if not content:
            print(f"[yellow]⚠️ Empty file: {file_path}[/yellow]")
            return True  # Consider it successful, nothing to do

        # Get the number of tokens for cost estimations
        num_tokens = num_tokens_from_string(content)

        print(
            f"[blue]Embedding the context from: {file_path}, {model_name}, tokens: {num_tokens}[/blue]"
        )

        # Get the embedding model
        embedding_model = llm.get_embedding_model(model_name)

        # Create metadata
        metadata = {
            "path": file_path,
            "tokens": num_tokens,
            "timestamp": asyncio.get_event_loop().time(),
        }

        # Use a dedicated connection with appropriate settings
        with get_db_connection(db_path, timeout=60.0) as conn:
            db = sqlite_utils.Database(conn)
            # Get or create the collection
            collection = llm.Collection(collection_name, db, model=embedding_model)
            # Embed the content and store in the collection
            collection.embed(file_id, content, metadata=metadata, store=True)
            return True

    except Exception as e:
        print(f"[yellow]⚠️ Failed to embed {file_path}: {str(e)}[/yellow]")
        return False


async def embed_files_batch(files, model_name, db_path, collection_name, batch_size=5):
    """Embed multiple files in batches for better performance"""
    try:
        if not files:
            return []

        # Get the embedding model
        embedding_model = llm.get_embedding_model(model_name)

        # Prepare the batch data
        batch_data = []
        for file_path in files:
            try:
                # Calculate the file ID (relative path)
                file_id = os.path.relpath(file_path, os.getcwd())

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Skip empty files
                if not content:
                    print(f"[yellow]⚠️ Empty file: {file_path}[/yellow]")
                    continue

                # Get the number of tokens for cost estimations
                num_tokens = num_tokens_from_string(content)

                metadata = {
                    "path": file_path,
                    "tokens": num_tokens,
                    "timestamp": asyncio.get_event_loop().time(),
                }

                # Add to batch
                batch_data.append((file_id, content, metadata))

                print(
                    f"[blue]Preparing to embed: {file_path}, tokens: {num_tokens}[/blue]"
                )
            except Exception as e:
                print(f"[yellow]⚠️ Failed to prepare {file_path}: {str(e)}[/yellow]")

        # Process files sequentially to avoid locking issues
        results = []
        for i, (file_id, content, meta) in enumerate(batch_data):
            print(f"[green]Processing file {i+1}/{len(batch_data)} - {file_id}[/green]")

            # Use a dedicated connection with appropriate settings
            try:
                with get_db_connection(db_path, timeout=30.0) as conn:
                    db = sqlite_utils.Database(conn)
                    collection = llm.Collection(
                        collection_name, db, model=embedding_model
                    )
                    collection.embed(file_id, content, metadata=meta, store=True)
                    results.append(True)
                    print(f"[green]✓ Successfully embedded {file_id}[/green]")
            except Exception as e:
                print(f"[red]❌ Failed to embed {file_id}: {str(e)}[/red]")
                results.append(False)

            # Add delay between files to reduce contention
            await asyncio.sleep(0.5)

        return results
    except Exception as e:
        print(f"[red]Error in batch embedding: {str(e)}[/red]")
        return [False] * len(files)


# FUNCTIONS FOR CHUNKS


@with_retry(max_retries=5, initial_delay=1.0)
async def embed_chunk(
    chunk_id, content, metadata, model_name, db_path, collection_name
):
    """Embed a single chunk with retry logic"""
    print(
        f"[blue]Embedding chunk: {chunk_id}, tokens: {metadata.get('tokens', 0)}[/blue]"
    )

    # Get the embedding model
    embedding_model = llm.get_embedding_model(model_name)

    with get_db_connection(db_path, timeout=30.0) as conn:
        db = sqlite_utils.Database(conn)
        collection = llm.Collection(collection_name, db, model=embedding_model)
        collection.embed(chunk_id, content, metadata=metadata, store=True)

    return True


async def embed_chunks(file_path, model_name, db_path, collection_name):
    """Extract and embed code chunks from a file"""
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            print(f"[yellow]⚠️ File not found: {file_path}[/yellow]")
            return False

        # Calculate the file ID (relative path)
        file_id = os.path.relpath(file_path, os.getcwd())

        print(f"[blue]Extracting chunks from: {file_path}[/blue]")

        # Extract chunks using Tree-sitter or fallback to regex
        chunks = treesitter_utils.extract_chunks_from_file(file_path)

        if not chunks:
            print(f"[yellow]⚠️ No chunks extracted from: {file_path}[/yellow]")
            return False

        print(f"[green]✓ Extracted {len(chunks)} chunks from {file_path}[/green]")

        # Get the embedding model
        embedding_model = llm.get_embedding_model(model_name)

        # Set up the chunk tables first, before doing any embedding
        db_utils.setup_chunk_tables(db_path)

        # Embed each chunk one at a time
        successfully_embedded = []
        for chunk in chunks:
            try:
                chunk_id = chunk["id"]
                content = chunk["content"]

                # Skip empty chunks
                if not content.strip():
                    continue

                # Get the number of tokens for cost estimations
                num_tokens = num_tokens_from_string(content)

                # Add to metadata
                chunk["metadata"] = {
                    "tokens": num_tokens,
                    "type": chunk["type"],
                    "name": chunk["name"],
                    "path": chunk["path"],
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "parent_id": chunk.get("parent_id"),
                    "timestamp": asyncio.get_event_loop().time(),
                }

                # Attempt to embed with retries
                try:
                    success = await embed_chunk(
                        chunk_id,
                        content,
                        chunk["metadata"],
                        model_name,
                        db_path,
                        collection_name,
                    )
                    if success:
                        successfully_embedded.append(chunk)
                        # Small delay between embeddings to reduce contention
                        await asyncio.sleep(0.5)
                except Exception as err:
                    print(
                        f"[yellow]⚠️ Failed to embed chunk {chunk_id}: {str(err)}[/yellow]"
                    )

            except Exception as e:
                print(
                    f"[yellow]⚠️ Failed to process chunk {chunk.get('id', 'unknown')}: {str(e)}[/yellow]"
                )

        # Store chunks in the chunks table only once, after all embeddings
        if successfully_embedded:
            # Use a separate connection for storing chunks to avoid locks
            with get_db_connection(db_path, timeout=30.0) as conn:
                db = sqlite_utils.Database(conn)
                # Store chunks with a dedicated connection
                db_utils.store_chunks_with_db(
                    db, collection_name, successfully_embedded
                )

        return (
            len(successfully_embedded) > 0
        )  # Success if at least one chunk was embedded
    except Exception as e:
        print(f"[yellow]⚠️ Failed to process chunks from {file_path}: {str(e)}[/yellow]")
        return False


async def embed_chunks_batch(files, model_name, db_path, collection_name, batch_size=5):
    """Extract and embed code chunks from multiple files in batches"""
    try:
        if not files:
            return []

        # Process files sequentially to avoid database contention
        results = []
        for i, file_path in enumerate(files):
            print(f"[blue]Processing file {i+1}/{len(files)}: {file_path}[/blue]")

            # Process chunks for each file individually
            success = await embed_chunks(
                file_path, model_name, db_path, collection_name
            )
            results.append(success)

            # Add a delay between files to reduce database contention
            await asyncio.sleep(1.0)

        return results
    except Exception as e:
        print(f"[red]Error in batch chunk embedding: {str(e)}[/red]")
        return [False] * len(files)


def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
