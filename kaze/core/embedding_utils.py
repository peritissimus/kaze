import llm
import os
import sqlite_utils
from rich import print
import tiktoken
import asyncio
import sqlite3

from kaze.core import treesitter_utils, db_utils


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

        # Connect to the database with increased timeout
        db = sqlite_utils.Database(db_path)

        # Configure SQLite for better concurrency handling
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=NORMAL")
        db.execute("PRAGMA busy_timeout=5000")

        # Get or create the collection
        collection = llm.Collection(collection_name, db, model=embedding_model)

        # Embed the content and store in the collection
        metadata = {
            "path": file_path,
            "tokens": num_tokens,
            "timestamp": asyncio.get_event_loop().time(),
        }

        max_retries = 3
        retry_delay = 2

        for retry in range(max_retries):
            try:
                collection.embed(file_id, content, metadata=metadata, store=True)
                return True  # Success
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and retry < max_retries - 1:
                    print(
                        f"[yellow]⚠️ Database locked, retrying in {retry_delay}s (attempt {retry+1}/{max_retries})[/yellow]"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise

        return False  # All retries failed
    except Exception as e:
        print(f"[yellow]⚠️ Failed to embed {file_path}: {str(e)}[/yellow]")
        return False  # Failure


async def embed_files_batch(files, model_name, db_path, collection_name, batch_size=5):
    """Embed multiple files in batches for better performance"""
    try:
        if not files:
            return []

        # Get the embedding model
        embedding_model = llm.get_embedding_model(model_name)

        # Connect to the database with increased timeout
        db = sqlite_utils.Database(db_path)

        # Configure SQLite for better concurrency
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=NORMAL")
        db.execute("PRAGMA busy_timeout=5000")

        # Get or create the collection
        collection = llm.Collection(collection_name, db, model=embedding_model)

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

        # Process in smaller batches to avoid locking issues
        results = []
        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i : i + batch_size]
            print(
                f"[green]Processing batch {i // batch_size + 1}/{(len(batch_data) - 1) // batch_size + 1} - {len(batch)} files[/green]"
            )

            # Process each file in the batch sequentially to reduce locking
            batch_results = []
            for file_id, content, meta in batch:
                try:
                    max_retries = 3
                    retry_delay = 2
                    success = False

                    for retry in range(max_retries):
                        try:
                            # Create a new connection for each file to prevent locks
                            retry_db = sqlite_utils.Database(db_path)
                            retry_collection = llm.Collection(
                                collection_name, retry_db, model=embedding_model
                            )

                            retry_collection.embed(
                                file_id, content, metadata=meta, store=True
                            )
                            batch_results.append(True)
                            success = True
                            break  # Exit retry loop on success
                        except sqlite3.OperationalError as e:
                            if (
                                "database is locked" in str(e)
                                and retry < max_retries - 1
                            ):
                                print(
                                    f"[yellow]⚠️ Database locked, retrying {file_id} in {retry_delay}s (attempt {retry+1}/{max_retries})[/yellow]"
                                )
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                            else:
                                raise

                    if not success:
                        print(
                            f"[red]Failed to embed {file_id} after {max_retries} retries[/red]"
                        )
                        batch_results.append(False)

                    # Add delay between files to avoid contention
                    await asyncio.sleep(0.5)

                except Exception as single_e:
                    print(
                        f"[red]Individual embedding failed for {file_id}: {str(single_e)}[/red]"
                    )
                    batch_results.append(False)

            results.extend(batch_results)

        return results
    except Exception as e:
        print(f"[red]Error in batch embedding: {str(e)}[/red]")
        return [False] * len(files)


# FUNCTIONS FOR CHUNKS


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

        # Connect to the database with a longer timeout and improved settings
        db = sqlite_utils.Database(db_path)

        # Ensure the database is not in WAL mode which can cause locking issues
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=NORMAL")
        db.execute("PRAGMA busy_timeout=5000")

        # Set up the chunk tables first, before doing any embedding
        db_utils.setup_chunk_tables(db_path)

        # Get or create the collection
        collection = llm.Collection(collection_name, db, model=embedding_model)

        # Embed each chunk with retry logic
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

                # Embed the chunk with retry logic
                max_retries = 3
                retry_delay = 2
                success = False

                for retry in range(max_retries):
                    try:
                        print(
                            f"[blue]Embedding chunk: {chunk_id}, tokens: {num_tokens}[/blue]"
                        )

                        # Create a new database connection for each embedding to avoid locks
                        retry_db = sqlite_utils.Database(db_path)
                        retry_collection = llm.Collection(
                            collection_name, retry_db, model=embedding_model
                        )

                        retry_collection.embed(
                            chunk_id, content, metadata=chunk["metadata"], store=True
                        )

                        successfully_embedded.append(chunk)
                        success = True
                        break
                    except sqlite3.OperationalError as e:
                        if "database is locked" in str(e) and retry < max_retries - 1:
                            print(
                                f"[yellow]⚠️ Database locked, retrying in {retry_delay}s (attempt {retry+1}/{max_retries})[/yellow]"
                            )
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            raise

                if not success:
                    print(
                        f"[yellow]⚠️ Failed to embed chunk {chunk_id} after {max_retries} retries[/yellow]"
                    )

                # Add a small delay between embeddings to reduce contention
                await asyncio.sleep(0.2)

            except Exception as e:
                print(
                    f"[yellow]⚠️ Failed to embed chunk {chunk.get('id', 'unknown')}: {str(e)}[/yellow]"
                )

        # Store chunks in the chunks table only once, after all embeddings
        if successfully_embedded:
            db_utils.store_chunks(db_path, collection_name, successfully_embedded)

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

        # Process files sequentially instead of parallel to reduce database contention
        results = []
        for file_path in files:
            # Process chunks for each file individually
            success = await embed_chunks(
                file_path, model_name, db_path, collection_name
            )
            results.append(success)

            # Small pause to avoid overwhelming the system
            await asyncio.sleep(0.5)

        return results
    except Exception as e:
        print(f"[red]Error in batch chunk embedding: {str(e)}[/red]")
        return [False] * len(files)


def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
