import llm
import os
import sqlite_utils
from rich import print
import tiktoken
import asyncio

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

        # Connect to the database
        db = sqlite_utils.Database(db_path)

        # Get or create the collection
        collection = llm.Collection(collection_name, db, model=embedding_model)

        # Embed the content and store in the collection
        metadata = {
            "path": file_path,
            "tokens": num_tokens,
            "timestamp": asyncio.get_event_loop().time(),
        }

        collection.embed(file_id, content, metadata=metadata, store=True)

        return True  # Success
    except Exception as e:
        print(f"[yellow]⚠️ Failed to embed {file_path}: {e}[/yellow]")
        return False  # Failure


async def embed_files_batch(files, model_name, db_path, collection_name, batch_size=20):
    """Embed multiple files in batches for better performance"""
    try:
        if not files:
            return []

        # Get the embedding model
        embedding_model = llm.get_embedding_model(model_name)

        # Connect to the database
        db = sqlite_utils.Database(db_path)

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
                print(f"[yellow]⚠️ Failed to prepare {file_path}: {e}[/yellow]")

        # Process in batches
        results = []
        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i : i + batch_size]
            print(
                f"[green]Processing batch {i // batch_size + 1}/{(len(batch_data) - 1) // batch_size + 1}[/green]"
            )

            try:
                # Use embed_multi_with_metadata for better performance
                collection.embed_multi_with_metadata(
                    [(id, content, meta) for id, content, meta in batch],
                    store=True,
                    batch_size=batch_size,
                )

                # Mark successful embeddings
                results.extend([True] * len(batch))
            except Exception as e:
                print(f"[red]Batch embedding failed: {e}[/red]")
                # In case of batch failure, try individual files
                for file_id, content, metadata in batch:
                    try:
                        collection.embed(
                            file_id, content, metadata=metadata, store=True
                        )
                        results.append(True)
                    except Exception as single_e:
                        print(
                            f"[red]Individual embedding failed for {file_id}: {single_e}[/red]"
                        )
                        results.append(False)

        return results
    except Exception as e:
        print(f"[red]Error in batch embedding: {e}[/red]")
        return [False] * len(files)


# NEW FUNCTIONS FOR CHUNKS


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

        # Extract chunks using Tree-sitter
        chunks = treesitter_utils.extract_chunks_from_file(file_path)

        if not chunks:
            print(f"[yellow]⚠️ No chunks extracted from: {file_path}[/yellow]")
            return False

        print(f"[green]✓ Extracted {len(chunks)} chunks from {file_path}[/green]")

        # Get the embedding model
        embedding_model = llm.get_embedding_model(model_name)

        # Connect to the database
        db = sqlite_utils.Database(db_path)

        # Get or create the collection
        collection = llm.Collection(collection_name, db, model=embedding_model)

        # Embed each chunk
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

                # Embed the chunk
                print(f"[blue]Embedding chunk: {chunk_id}, tokens: {num_tokens}[/blue]")
                collection.embed(
                    chunk_id, content, metadata=chunk["metadata"], store=True
                )

                successfully_embedded.append(chunk)
            except Exception as e:
                print(
                    f"[yellow]⚠️ Failed to embed chunk {chunk.get('id', 'unknown')}: {e}[/yellow]"
                )

        # Store chunks in the chunks table
        if successfully_embedded:
            db_utils.store_chunks(db_path, collection_name, successfully_embedded)

        return (
            len(successfully_embedded) > 0
        )  # Success if at least one chunk was embedded
    except Exception as e:
        print(f"[yellow]⚠️ Failed to process chunks from {file_path}: {e}[/yellow]")
        return False


async def embed_chunks_batch(
    files, model_name, db_path, collection_name, batch_size=20
):
    """Extract and embed code chunks from multiple files in batches"""
    try:
        if not files:
            return []

        results = []
        for file_path in files:
            # Process chunks for each file individually
            success = await embed_chunks(
                file_path, model_name, db_path, collection_name
            )
            results.append(success)

            # Small pause to avoid overwhelming the system
            await asyncio.sleep(0.1)

        return results
    except Exception as e:
        print(f"[red]Error in batch chunk embedding: {e}[/red]")
        return [False] * len(files)


def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
