import llm
import sqlite3
from rich import print


def query_embeddings(db_path, collection_name, query_text, limit, threshold):
    """Queries the embeddings database and returns results."""
    try:
        results = llm.get_nearest(
            collection_name,
            query_text,
            database=db_path,
            limit=limit,
            threshold=threshold,
        )
        # Convert the results from the llm into a list of json serialziable dictionaries
        serializable_results = [dict(r) for r in results]
        return serializable_results
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


def show_collections(db_path):
    """Lists the collections in the database."""
    try:
        collections = llm.collections.list(database=db_path)
        if not collections:
            print("   [yellow]No collections found[/yellow]")
        else:
            for collection in collections:
                count = get_collection_count(db_path, collection)
                print(f"   - [cyan]{collection}[/cyan]: [yellow]{count}[/yellow] files")
    except Exception as e:
        print(f"[red]Error listing collections: {e}[/red]")


def get_collection_count(db_path, collection):
    """Gets the number of entries in a collection."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {collection}")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"[red]Error getting collection count: {e}[/red]")
        return 0
