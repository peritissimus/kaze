import llm
import sqlite3
import sqlite_utils
from rich import print
from typing import Dict, List, Any, Optional


def query_embeddings(db_path, collection_name, query_text, limit, threshold):
    """Queries the embeddings database and returns results using the Collection class approach."""
    try:
        # Connect to the database
        db = sqlite_utils.Database(db_path)

        # Check if collection exists
        if not llm.Collection.exists(db, collection_name):
            print(
                f"[red]Collection '{collection_name}' does not exist in the database[/red]"
            )
            return []

        # Get the collection
        collection = llm.Collection(collection_name, db)

        # Query for similar documents
        results = collection.similar(query_text, number=limit)

        # Filter by threshold and convert to serializable dictionaries
        serializable_results = []
        for entry in results:
            if entry.score >= threshold:
                result_dict = {
                    "id": entry.id,
                    "score": entry.score,
                    "content": entry.content,  # Will be None if not stored
                    "metadata": entry.metadata,  # Will be None if not stored
                }
                serializable_results.append(result_dict)

        return serializable_results
    except sqlite3.OperationalError as e:
        print(f"[red]Database error: {e}[/red]")
        return []
    except Exception as e:
        print(f"[red]Error querying embeddings: {e}[/red]")
        return []


def get_db_size(db_path):
    """
    Returns the size of the file in human readable format
    """
    import os, math

    file_size = os.path.getsize(db_path)
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(file_size, 1024)))
    p = math.pow(1024, i)
    s = round(file_size / p, 2)
    return f"{s} {size_name[i]}"


def list_collections(db):
    """List all collections in the database."""
    try:
        tables = [
            t["name"]
            for t in db.query("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        if "collections" in tables:
            rows = db.query("SELECT name FROM collections")
            return [row["name"] for row in rows]
        return []
    except Exception as e:
        print(f"[red]Error listing collections: {e}[/red]")
        return []


def show_collections(db_path):
    """Lists the collections in the database."""
    try:
        # Connect to the database
        db = sqlite_utils.Database(db_path)

        # Get collections
        collections = list_collections(db)

        if not collections:
            print("   [yellow]No collections found[/yellow]")
        else:
            for collection in collections:
                try:
                    # Get the collection
                    coll = llm.Collection(collection, db)
                    count = coll.count()
                    print(
                        f"   - [cyan]{collection}[/cyan]: [yellow]{count}[/yellow] files"
                    )
                except Exception as e:
                    print(
                        f"   - [cyan]{collection}[/cyan]: [red]Error getting count: {e}[/red]"
                    )
    except Exception as e:
        print(f"[red]Error listing collections: {e}[/red]")


def get_collection_count(db_path, collection_name):
    """Gets the number of entries in a collection using the Collection class."""
    try:
        # Connect to the database
        db = sqlite_utils.Database(db_path)

        # Check if collection exists
        if not llm.Collection.exists(db, collection_name):
            return 0

        # Get the collection and count
        collection = llm.Collection(collection_name, db)
        return collection.count()
    except Exception as e:
        print(f"[red]Error getting collection count: {e}[/red]")
        return 0


def get_collection_model(db_path, collection_name):
    """Gets the embedding model used for a collection."""
    try:
        # Connect to the database
        db = sqlite_utils.Database(db_path)

        # Check if collection exists
        if not llm.Collection.exists(db, collection_name):
            return None

        # Get the collection
        collection = llm.Collection(collection_name, db)
        return collection.model_id
    except Exception as e:
        print(f"[red]Error getting collection model: {e}[/red]")
        return None


def find_most_similar(db_path, collection_name, query_text, limit=1):
    """Finds the single most similar document to the query text."""
    results = query_embeddings(db_path, collection_name, query_text, limit, 0.0)
    return results[0] if results else None


# NEW FUNCTIONS FOR CHUNKS
def setup_chunk_tables(db_path):
    """Set up database tables for storing code chunks."""
    try:
        # Connect to the database
        db = sqlite_utils.Database(db_path)

        # Create the chunks table if it doesn't exist
        db["chunks"].create(
            {
                "id": str,
                "collection_id": int,
                "type": str,
                "name": str,
                "path": str,
                "start_line": int,
                "start_col": int,
                "end_line": int,
                "end_col": int,
                "parent_id": str,
                "content": str,
                "metadata": str,  # JSON
                "updated": int,  # Timestamp
            },
            pk="id",
            if_not_exists=True,
            foreign_keys=[("collection_id", "collections", "id")],
        )

        # Create an index on the parent_id column
        db["chunks"].create_index(["parent_id"], if_not_exists=True)

        # Create an index on the path column
        db["chunks"].create_index(["path"], if_not_exists=True)

        # Create an index on the type column
        db["chunks"].create_index(["type"], if_not_exists=True)

        print(f"[green]✓ Set up chunk tables in {db_path}[/green]")
        return True
    except Exception as e:
        print(f"[red]❌ Error setting up chunk tables: {e}[/red]")
        return False


def store_chunks(db_path, collection_name, chunks):
    """Store code chunks in the database."""
    try:
        # Connect to the database
        db = sqlite_utils.Database(db_path)

        # Check if collection exists
        if not llm.Collection.exists(db, collection_name):
            print(
                f"[red]Collection '{collection_name}' does not exist in the database[/red]"
            )
            return False

        # Get the collection ID
        collection_id = db.query(
            "SELECT id FROM collections WHERE name = ?", [collection_name]
        ).fetchone()["id"]

        # Set up the chunk tables
        setup_chunk_tables(db_path)

        # Prepare chunks for insertion
        import json
        import time

        now = int(time.time())

        chunk_rows = []
        for chunk in chunks:
            chunk_row = {
                "id": chunk["id"],
                "collection_id": collection_id,
                "type": chunk["type"],
                "name": chunk["name"],
                "path": chunk["path"],
                "start_line": chunk["start_line"],
                "start_col": chunk["start_col"],
                "end_line": chunk["end_line"],
                "end_col": chunk["end_col"],
                "parent_id": chunk.get("parent_id"),
                "content": chunk["content"],
                "metadata": json.dumps(chunk.get("metadata", {})),
                "updated": now,
            }
            chunk_rows.append(chunk_row)

        # Insert chunks in batches
        batch_size = 100
        for i in range(0, len(chunk_rows), batch_size):
            batch = chunk_rows[i : i + batch_size]
            db["chunks"].upsert_all(batch, pk="id", alter=True)

        print(
            f"[green]✓ Stored {len(chunks)} chunks in collection '{collection_name}'[/green]"
        )
        return True
    except Exception as e:
        print(f"[red]❌ Error storing chunks: {e}[/red]")
        return False


def query_chunks(
    db_path,
    collection_name,
    query_text,
    limit,
    threshold,
    chunk_type=None,
    parent_id=None,
):
    """Query for similar chunks."""
    try:
        # Connect to the database
        db = sqlite_utils.Database(db_path)

        # Check if collection exists
        if not llm.Collection.exists(db, collection_name):
            print(
                f"[red]Collection '{collection_name}' does not exist in the database[/red]"
            )
            return []

        # Get the collection
        collection = llm.Collection(collection_name, db)

        # Query for similar documents
        results = collection.similar(
            query_text, number=limit * 2
        )  # Get more to allow for filtering

        # Filter by threshold and convert to serializable dictionaries
        serializable_results = []

        for entry in results:
            if entry.score < threshold:
                continue

            # Get the chunk from the chunks table
            try:
                chunk_row = db.query(
                    "SELECT * FROM chunks WHERE id = ? AND collection_id = (SELECT id FROM collections WHERE name = ?)",
                    [entry.id, collection_name],
                ).fetchone()

                if not chunk_row:
                    continue

                # Apply filters
                if chunk_type and chunk_row["type"] != chunk_type:
                    continue

                if parent_id is not None and chunk_row["parent_id"] != parent_id:
                    continue

                # Convert to dictionary
                import json

                result_dict = dict(chunk_row)
                result_dict["score"] = entry.score
                result_dict["metadata"] = json.loads(result_dict["metadata"])

                serializable_results.append(result_dict)

                # Stop if we've reached the limit
                if len(serializable_results) >= limit:
                    break
            except Exception as inner_e:
                print(
                    f"[yellow]⚠️ Error processing chunk {entry.id}: {inner_e}[/yellow]"
                )

        return serializable_results
    except sqlite3.OperationalError as e:
        print(f"[red]Database error: {e}[/red]")
        return []
    except Exception as e:
        print(f"[red]Error querying chunks: {e}[/red]")
        return []


def get_chunks_by_path(db_path, collection_name, file_path):
    """Get all chunks for a specific file path."""
    try:
        # Connect to the database
        db = sqlite_utils.Database(db_path)

        # Check if collection exists
        if not llm.Collection.exists(db, collection_name):
            print(
                f"[red]Collection '{collection_name}' does not exist in the database[/red]"
            )
            return []

        # Get the collection ID
        collection_id = db.query(
            "SELECT id FROM collections WHERE name = ?", [collection_name]
        ).fetchone()["id"]

        # Query for chunks by path
        import json

        chunk_rows = list(
            db.query(
                "SELECT * FROM chunks WHERE path = ? AND collection_id = ?",
                [file_path, collection_id],
            )
        )

        # Convert to dictionaries
        chunks = []
        for row in chunk_rows:
            chunk_dict = dict(row)
            chunk_dict["metadata"] = json.loads(chunk_dict["metadata"])
            chunks.append(chunk_dict)

        return chunks
    except Exception as e:
        print(f"[red]Error getting chunks by path: {e}[/red]")
        return []


def get_chunk_count(db_path, collection_name):
    """Get the number of chunks in a collection."""
    try:
        # Connect to the database
        db = sqlite_utils.Database(db_path)

        # Check if collection exists
        if not llm.Collection.exists(db, collection_name):
            print(
                f"[red]Collection '{collection_name}' does not exist in the database[/red]"
            )
            return 0

        # Get the collection ID
        collection_id = db.query(
            "SELECT id FROM collections WHERE name = ?", [collection_name]
        ).fetchone()["id"]

        # Count chunks
        count = db.query(
            "SELECT COUNT(*) as count FROM chunks WHERE collection_id = ?",
            [collection_id],
        ).fetchone()["count"]

        return count
    except Exception as e:
        print(f"[red]Error getting chunk count: {e}[/red]")
        return 0
