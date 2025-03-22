import llm
import sqlite3
import sqlite_utils
from rich import print


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
        print(f"[red]Database error: {str(e)}[/red]")
        return []
    except Exception as e:
        print(f"[red]Error querying embeddings: {str(e)}[/red]")
        return []


def get_db_size(db_path):
    """
    Returns the size of the file in human readable format
    """
    import os
    import math

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
        print(f"[red]Error listing collections: {str(e)}[/red]")
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
                        f"   - [cyan]{collection}[/cyan]: [red]Error getting count: {str(e)}[/red]"
                    )
    except Exception as e:
        print(f"[red]Error listing collections: {str(e)}[/red]")


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
        print(f"[red]Error getting collection count: {str(e)}[/red]")
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
        print(f"[red]Error getting collection model: {str(e)}[/red]")
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
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                collection_id INTEGER,
                type TEXT,
                name TEXT,
                path TEXT,
                start_line INTEGER,
                start_col INTEGER,
                end_line INTEGER,
                end_col INTEGER,
                parent_id TEXT,
                content TEXT,
                metadata TEXT,
                updated INTEGER,
                FOREIGN KEY (collection_id) REFERENCES collections(id)
            )
            """
        )

        # Create indexes
        db.execute("CREATE INDEX IF NOT EXISTS chunks_parent_id ON chunks(parent_id)")
        db.execute("CREATE INDEX IF NOT EXISTS chunks_path ON chunks(path)")
        db.execute("CREATE INDEX IF NOT EXISTS chunks_type ON chunks(type)")

        print(f"[green]✓ Set up chunk tables in {db_path}[/green]")
        return True
    except Exception as e:
        print(f"[red]❌ Error setting up chunk tables: {str(e)}[/red]")
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
        collection_rows = list(
            db.query("SELECT id FROM collections WHERE name = ?", [collection_name])
        )
        if not collection_rows:
            print(f"[red]Collection '{collection_name}' not found in database[/red]")
            return False

        collection_id = collection_rows[0]["id"]

        # Set up the chunk tables
        setup_chunk_tables(db_path)

        # Prepare chunks for insertion
        import json
        import time

        now = int(time.time())

        # Insert chunks one by one (not the most efficient, but most compatible)
        for chunk in chunks:
            db.execute(
                """
                INSERT OR REPLACE INTO chunks 
                (id, collection_id, type, name, path, start_line, start_col, 
                end_line, end_col, parent_id, content, metadata, updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    chunk["id"],
                    collection_id,
                    chunk["type"],
                    chunk["name"],
                    chunk["path"],
                    chunk["start_line"],
                    chunk["start_col"],
                    chunk["end_line"],
                    chunk["end_col"],
                    chunk.get("parent_id"),
                    chunk["content"],
                    json.dumps(chunk.get("metadata", {})),
                    now,
                ],
            )

        print(
            f"[green]✓ Stored {len(chunks)} chunks in collection '{collection_name}'[/green]"
        )
        return True
    except Exception as e:
        print(f"[red]❌ Error storing chunks: {str(e)}[/red]")
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
                chunk_rows = list(
                    db.query(
                        "SELECT * FROM chunks WHERE id = ? AND collection_id = (SELECT id FROM collections WHERE name = ?)",
                        [entry.id, collection_name],
                    )
                )

                if not chunk_rows:
                    continue

                chunk_row = chunk_rows[0]

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
                    f"[yellow]⚠️ Error processing chunk {entry.id}: {str(inner_e)}[/yellow]"
                )

        return serializable_results
    except sqlite3.OperationalError as e:
        print(f"[red]Database error: {str(e)}[/red]")
        return []
    except Exception as e:
        print(f"[red]Error querying chunks: {str(e)}[/red]")
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
        collection_rows = list(
            db.query("SELECT id FROM collections WHERE name = ?", [collection_name])
        )
        if not collection_rows:
            print(f"[red]Collection '{collection_name}' not found in database[/red]")
            return []

        collection_id = collection_rows[0]["id"]

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
        print(f"[red]Error getting chunks by path: {str(e)}[/red]")
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
        collection_rows = list(
            db.query("SELECT id FROM collections WHERE name = ?", [collection_name])
        )
        if not collection_rows:
            print(f"[red]Collection '{collection_name}' not found in database[/red]")
            return 0

        collection_id = collection_rows[0]["id"]

        # Count chunks
        count_rows = list(
            db.query(
                "SELECT COUNT(*) as count FROM chunks WHERE collection_id = ?",
                [collection_id],
            )
        )

        count = count_rows[0]["count"] if count_rows else 0

        return count
    except Exception as e:
        print(f"[red]Error getting chunk count: {str(e)}[/red]")
        return 0


def store_chunks_with_db(db, collection_name, chunks):
    """
    Store code chunks using an existing database connection.

    Args:
        db: A sqlite_utils.Database instance with an active connection
        collection_name: Name of the collection to store chunks in
        chunks: List of chunk dictionaries to store

    Returns:
        Boolean indicating success or failure
    """
    try:
        # Check if collection exists
        if not llm.Collection.exists(db, collection_name):
            print(
                f"[red]Collection '{collection_name}' does not exist in the database[/red]"
            )
            return False

        # Get the collection ID
        collection_rows = list(
            db.query("SELECT id FROM collections WHERE name = ?", [collection_name])
        )
        if not collection_rows:
            print(f"[red]Collection '{collection_name}' not found in database[/red]")
            return False

        collection_id = collection_rows[0]["id"]

        # Set up the chunk tables (using the existing db connection)
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                collection_id INTEGER,
                type TEXT,
                name TEXT,
                path TEXT,
                start_line INTEGER,
                start_col INTEGER,
                end_line INTEGER,
                end_col INTEGER,
                parent_id TEXT,
                content TEXT,
                metadata TEXT,
                updated INTEGER,
                FOREIGN KEY (collection_id) REFERENCES collections(id)
            )
            """
        )

        # Create indexes if they don't exist
        db.execute("CREATE INDEX IF NOT EXISTS chunks_parent_id ON chunks(parent_id)")
        db.execute("CREATE INDEX IF NOT EXISTS chunks_path ON chunks(path)")
        db.execute("CREATE INDEX IF NOT EXISTS chunks_type ON chunks(type)")

        # Prepare chunks for insertion
        import json
        import time

        now = int(time.time())

        # Begin transaction for bulk insert
        with db.conn:  # This ensures proper transaction handling
            # Insert chunks one by one
            for chunk in chunks:
                db.execute(
                    """
                    INSERT OR REPLACE INTO chunks 
                    (id, collection_id, type, name, path, start_line, start_col, 
                    end_line, end_col, parent_id, content, metadata, updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        chunk["id"],
                        collection_id,
                        chunk["type"],
                        chunk["name"],
                        chunk["path"],
                        chunk["start_line"],
                        chunk["start_col"],
                        chunk["end_line"],
                        chunk["end_col"],
                        chunk.get("parent_id"),
                        chunk["content"],
                        json.dumps(chunk.get("metadata", {})),
                        now,
                    ],
                )

        print(
            f"[green]✓ Stored {len(chunks)} chunks in collection '{collection_name}'[/green]"
        )
        return True
    except Exception as e:
        print(f"[red]❌ Error storing chunks: {str(e)}[/red]")
        return False
