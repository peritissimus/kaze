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
