"""
CLI commands for working with code chunks.
Provides commands for managing and querying hierarchical code chunks.
"""

import click
import os
import json
from rich import print
import asyncio
import sqlite_utils

from kaze.core import treesitter_utils, db_utils, embedding_utils, file_utils
from kaze.utils import chunk_helpers


@click.group()
def chunks():
    """Commands for working with code chunks."""
    pass


@chunks.command()
@click.option("-d", "--dir", "project_dir", default=".", help="Project directory.")
@click.option(
    "-o",
    "--output",
    "output_dir",
    default=None,
    help="Output directory (default: .kaze in project directory).",
)
@click.option(
    "-m", "--model", default="text-embedding-3-small", help="Embedding model to use."
)
@click.option("-s", "--size", default=100, type=int, help="Maximum file size in KB.")
@click.option("-b", "--batch", default=5, type=int, help="Batch size for processing.")
@click.option("-c", "--collection", default="chunks", help="Collection name.")
@click.option(
    "-f", "--force", is_flag=True, help="Force recreation of embeddings database."
)
@click.option(
    "--include",
    "include_pattern",
    default=None,
    help="Additional files to include (glob pattern).",
)
@click.option(
    "--exclude",
    "exclude_pattern",
    default=None,
    help="Additional files to exclude (glob pattern).",
)
@click.option(
    "--sequential",
    is_flag=True,
    default=True,
    help="Process files sequentially (recommended to avoid database locks).",
)
def create(
    project_dir,
    output_dir,
    model,
    size,
    batch,
    collection,
    force,
    include_pattern,
    exclude_pattern,
    sequential,
):
    """Create code chunk embeddings for files in the project."""
    project_dir = os.path.abspath(project_dir)
    kaze_dir = output_dir or os.path.join(project_dir, ".kaze")
    db_path = os.path.join(kaze_dir, "embeddings.db")

    print(f"[blue]🔍 Processing files in [cyan]{project_dir}[/cyan]")
    print(f"[blue]💾 Chunk embeddings will be saved to [cyan]{db_path}[/cyan]")
    print(f"[blue]🧠 Using model: [cyan]{model}[/cyan]")
    print(
        f"[blue]⚙️ Processing mode: [cyan]{'Sequential' if sequential else 'Batch'} (batch size: {batch})[/cyan]"
    )

    os.makedirs(kaze_dir, exist_ok=True)

    # Handle force flag - need to modify this to properly close connections
    if force and os.path.exists(db_path):
        print("[yellow]⚠️ Force flag set - removing existing database[/yellow]")
        # Ensure no connections to DB before removing
        try:
            # Try to release any existing connections explicitly
            import sqlite3

            conn = sqlite3.connect(db_path)
            conn.close()
            del conn
        except:
            pass

        # Small delay to ensure connections are closed
        import time

        time.sleep(0.5)

        try:
            os.remove(db_path)
            print("[green]✓ Removed existing database[/green]")
        except Exception as e:
            print(f"[red]❌ Error removing database: {str(e)}[/red]")
            print(
                "[yellow]⚠️ This may be due to open connections. Try closing them first.[/yellow]"
            )
            return

    elif os.path.exists(db_path):
        # Check if collection exists - using a more robust approach
        try:
            # Connect with a timeout to handle locks
            import sqlite3

            conn = sqlite3.connect(db_path, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")

            # Check for collection
            cursor.execute("SELECT name FROM collections WHERE name = ?", (collection,))
            result = cursor.fetchone()
            conn.close()

            if result:
                print(
                    f"[yellow]⚠️ Collection '{collection}' already exists in database[/yellow]"
                )
                print(
                    "   [yellow]Use [green]--force[/green] to recreate the collection[/yellow]"
                )
                return
        except Exception as e:
            print(f"[yellow]⚠️ Error checking collections: {str(e)}[/yellow]")
            print("   [yellow]Continuing with database creation[/yellow]")

    # Get file list
    file_list = file_utils.get_file_list(project_dir, include_pattern, exclude_pattern)

    # Update should_process_file max size from parameter
    file_utils.should_process_file.max_file_size_kb = size

    if not file_list:
        print("[yellow]⚠️ No suitable files found to process[/yellow]")
        return

    print(f"[green]📊 Found [yellow]{len(file_list)}[/yellow] files to process[/green]")

    # Filter for files that have supported parsers
    supported_files = []
    for file_path in file_list:
        language_id = treesitter_utils.detect_language(file_path)
        if language_id:
            supported_files.append(file_path)
        else:
            print(f"[yellow]⚠️ Skipping unsupported file type: {file_path}[/yellow]")

    if not supported_files:
        print("[yellow]⚠️ No supported files found to process[/yellow]")
        return

    print(
        f"[green]📊 Found [yellow]{len(supported_files)}[/yellow] supported files to process[/green]"
    )

    # Add handler for graceful shutdown with Ctrl+C
    import signal

    # Flag to track if processing should stop
    should_stop = False

    def signal_handler(sig, frame):
        nonlocal should_stop
        if not should_stop:
            print(
                "\n[yellow]⚠️ Received interrupt signal. Finishing current file and then exiting...[/yellow]"
            )
            should_stop = True
        else:
            print(
                "\n[red]❌ Forced exit. Database may be in an inconsistent state.[/red]"
            )
            import sys

            sys.exit(1)

    # Set up the signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Process files sequentially to avoid locking issues
    async def process_files_sequential():
        results = []

        for i, file_path in enumerate(supported_files):
            if should_stop:
                print("[yellow]⚠️ Processing stopped due to user interrupt[/yellow]")
                break

            print(
                f"[blue]Processing file {i+1}/{len(supported_files)}: {file_path}[/blue]"
            )

            # Process each file individually
            success = await embedding_utils.embed_chunks(
                file_path, model, db_path, collection
            )
            results.append(success)

            # Add a progress indicator
            success_count = results.count(True)
            fail_count = len(results) - success_count
            print(
                f"[green]Progress: {i+1}/{len(supported_files)} ({success_count} succeeded, {fail_count} failed)[/green]"
            )

        return results

    # Process files in batches (legacy mode, more prone to locking)
    async def process_files_batch():
        results = await embedding_utils.embed_chunks_batch(
            supported_files, model, db_path, collection, batch
        )
        return results

    # Choose the processing function based on the sequential flag
    processing_func = process_files_sequential if sequential else process_files_batch

    try:
        # Run the chosen processing function
        results = asyncio.run(processing_func())

        # Count successes and failures
        success_count = results.count(True) if results else 0
        fail_count = len(results) - success_count if results else 0

        print(
            f"\n[green]Processing complete! Successfully processed [yellow]{success_count}[/yellow] files, failed to process [yellow]{fail_count}[/yellow] files.[/green]"
        )

        if os.path.exists(db_path):
            print(
                f"[green]✅ Chunk embeddings successfully created and saved to [cyan]{db_path}[/cyan]"
            )
            print(
                f"[green]🔢 Database size: [yellow]{file_utils.get_file_size(db_path)}[/yellow][/green]"
            )

            # Connect with a timeout to avoid locks when showing collections
            try:
                import sqlite3

                conn = sqlite3.connect(db_path, timeout=5.0)
                db = sqlite_utils.Database(conn)

                print("[green]📚 Collections in database:[/green]")
                db_utils.show_collections(db_path)

                # Show chunk statistics - with a timeout
                chunk_count = db_utils.get_chunk_count(db_path, collection)
                print(f"[green]🧩 Total chunks: [yellow]{chunk_count}[/yellow][/green]")

                conn.close()
            except Exception as e:
                print(f"[yellow]⚠️ Error displaying database info: {str(e)}[/yellow]")
        else:
            print("[red]❌ Error: Failed to create embeddings database[/red]")

        print("[green]🎉 All done![/green]")

    except KeyboardInterrupt:
        print("\n[yellow]⚠️ Process interrupted by user[/yellow]")
    except Exception as e:
        print(f"[red]❌ Error processing files: {str(e)}[/red]")


@chunks.command()
@click.option("-d", "--dir", "project_dir", default=".", help="Project directory.")
@click.option(
    "-o",
    "--output",
    "output_dir",
    default=None,
    help="Output directory (default: .kaze in project directory).",
)
@click.option("-c", "--collection", default="chunks", help="Collection name.")
@click.option("-f", "--file", "file_path", help="Filter chunks by file path.")
@click.option(
    "-t", "--type", "chunk_type", help="Filter chunks by type (class, function, etc.)."
)
@click.option("--tree", is_flag=True, help="Display chunks as a tree.")
def list(
    project_dir,
    output_dir,
    collection,
    file_path,
    chunk_type,
    tree,
):
    """List code chunks in the database."""
    project_dir = os.path.abspath(project_dir)
    kaze_dir = output_dir or os.path.join(project_dir, ".kaze")
    db_path = os.path.join(kaze_dir, "embeddings.db")

    if not os.path.exists(db_path):
        print(f"[red]Error: Embeddings database not found at [cyan]{db_path}[/cyan]")
        print(
            "Run [green]kaze chunks create[/green] first to generate chunk embeddings."
        )
        return

    # Connect to the database
    db = sqlite_utils.Database(db_path)

    # Check if collection exists
    if collection not in db_utils.list_collections(db):
        print(f"[red]Error: Collection '{collection}' not found in database[/red]")
        return

    print(f"[blue]📊 Listing chunks in collection: [cyan]{collection}[/cyan]")

    try:
        # Query for chunks
        collection_rows = list(
            db.query("SELECT id FROM collections WHERE name = ?", [collection])
        )

        if not collection_rows:
            print(f"[red]Error: Collection '{collection}' not found in database[/red]")
            return

        collection_id = collection_rows[0]["id"]

        query = "SELECT * FROM chunks WHERE collection_id = ?"
        params = [collection_id]

        if file_path:
            query += " AND path LIKE ?"
            params.append(f"%{file_path}%")

        if chunk_type:
            query += " AND type = ?"
            params.append(chunk_type)

        # Execute the query
        chunk_rows = list(db.query(query, params))

        # Convert to dictionaries
        chunks = []
        for row in chunk_rows:
            chunk_dict = dict(row)
            chunk_dict["metadata"] = json.loads(chunk_dict["metadata"])
            chunks.append(chunk_dict)

        if not chunks:
            print("[yellow]⚠️ No chunks found matching the criteria.[/yellow]")
            return

        print(f"[green]📊 Found [yellow]{len(chunks)}[/yellow] chunks[/green]")

        # Display chunks
        if tree:
            # Display as a tree
            chunk_helpers.print_chunk_tree(chunks)
        else:
            # Display as a list
            for i, chunk in enumerate(chunks, 1):
                print(
                    f"[green]{i}.[/green] [cyan]{chunk['type']}[/cyan]:[yellow]{chunk['name']}[/yellow] "
                    f"({chunk['path']}:{chunk['start_line']}-{chunk['end_line']})"
                )

    except Exception as e:
        print(f"[red]Error listing chunks: {str(e)}[/red]")


@chunks.command()
@click.option("-d", "--dir", "project_dir", default=".", help="Project directory.")
@click.option(
    "-o",
    "--output",
    "output_dir",
    default=None,
    help="Output directory (default: .kaze in project directory).",
)
@click.option("-q", "--query", "query_text", required=True, help="Text to search for.")
@click.option("-n", "--limit", default=10, type=int, help="Maximum number of results.")
@click.option(
    "-t", "--threshold", default=0.2, type=float, help="Similarity threshold (0.0-1.0)."
)
@click.option("-c", "--collection", default="chunks", help="Collection to search in.")
@click.option(
    "-y", "--type", "chunk_type", help="Filter by chunk type (class, function, etc.)."
)
@click.option("--show-content", is_flag=True, help="Show chunk content in results.")
@click.option(
    "--human",
    "human_output",
    is_flag=True,
    default=True,
    help="Display human-readable output instead of JSON.",
)
def query(
    project_dir,
    output_dir,
    query_text,
    limit,
    threshold,
    collection,
    chunk_type,
    show_content,
    human_output,
):
    """Search for similar code chunks."""
    project_dir = os.path.abspath(project_dir)
    kaze_dir = output_dir or os.path.join(project_dir, ".kaze")
    db_path = os.path.join(kaze_dir, "embeddings.db")

    if not os.path.exists(db_path):
        if human_output:
            print(
                f"[red]Error: Embeddings database not found at [cyan]{db_path}[/cyan]"
            )
            print(
                "Run [green]kaze chunks create[/green] first to generate chunk embeddings."
            )
        else:
            print(json.dumps({"error": "Database not found", "path": db_path}))
        return

    # Connect to the database to check if collection exists
    db = sqlite_utils.Database(db_path)
    collections = db_utils.list_collections(db)

    if collection not in collections:
        if human_output:
            print(f"[red]Error: Collection '{collection}' not found in database[/red]")
            print(f"Available collections: {', '.join(collections)}")
        else:
            print(
                json.dumps(
                    {
                        "error": "Collection not found",
                        "name": collection,
                        "available": collections,
                    }
                )
            )
        return

    if human_output:
        print(f'[blue]🔍 Searching for: [cyan]"{query_text}"[/cyan]')
        print(f"[blue]📊 Using collection: [cyan]{collection}[/cyan]")
        print(f"[blue]📚 Maximum results: [cyan]{limit}[/cyan]")
        print(f"[blue]🎯 Similarity threshold: [cyan]{threshold}[/cyan]")
        if chunk_type:
            print(f"[blue]🧩 Filtering by chunk type: [cyan]{chunk_type}[/cyan]")

    # Get the results
    results = db_utils.query_chunks(
        db_path, collection, query_text, limit, threshold, chunk_type
    )

    if not results:
        if human_output:
            print("[yellow]⚠️ No chunks found matching your query.[/yellow]")
        else:
            print("[]")  # Empty JSON array
        return

    if human_output:
        # Display results
        print("[green]📋 Search results:[/green]")
        print("-------------------------------------------")

        for idx, chunk in enumerate(results, 1):
            score = chunk["score"]
            score_percent = round(score * 100, 1)

            # Display chunk information
            print(
                f"[{idx}] [cyan]{chunk['type']}[/cyan]:[yellow]{chunk['name']}[/yellow] "
                f"([yellow]{score_percent}%[/yellow] match)"
            )
            print(f"    File: [blue]{chunk['path']}[/blue]")
            print(
                f"    Lines: {chunk['start_line']}-{chunk['end_line']} "
                f"({chunk['end_line'] - chunk['start_line'] + 1} lines)"
            )

            if chunk.get("parent_id"):
                print(f"    Parent: [green]{chunk['parent_id']}[/green]")

            if show_content:
                chunk_helpers.display_chunk(chunk)

            print("-------------------------------------------")

        print(f"[green]🎉 Found {len(results)} matching chunks![/green]")
    else:
        print(json.dumps(results))


@chunks.command()
@click.option("-d", "--dir", "project_dir", default=".", help="Project directory.")
@click.option(
    "-o",
    "--output",
    "output_dir",
    default=None,
    help="Output directory (default: .kaze in project directory).",
)
@click.option("-c", "--collection", default="chunks", help="Collection name.")
@click.option("-i", "--id", "chunk_id", required=True, help="ID of the chunk to show.")
@click.option("--show-content", is_flag=True, default=True, help="Show chunk content.")
@click.option("--show-children", is_flag=True, help="Show chunk's children.")
@click.option("--show-ancestors", is_flag=True, help="Show chunk's ancestors.")
def show(
    project_dir,
    output_dir,
    collection,
    chunk_id,
    show_content,
    show_children,
    show_ancestors,
):
    """Show details of a specific chunk."""
    project_dir = os.path.abspath(project_dir)
    kaze_dir = output_dir or os.path.join(project_dir, ".kaze")
    db_path = os.path.join(kaze_dir, "embeddings.db")

    if not os.path.exists(db_path):
        print(f"[red]Error: Embeddings database not found at [cyan]{db_path}[/cyan]")
        print(
            "Run [green]kaze chunks create[/green] first to generate chunk embeddings."
        )
        return

    # Connect to the database
    db = sqlite_utils.Database(db_path)

    # Check if collection exists
    if collection not in db_utils.list_collections(db):
        print(f"[red]Error: Collection '{collection}' not found in database[/red]")
        return

    # Get the collection ID
    collection_rows = list(
        db.query("SELECT id FROM collections WHERE name = ?", [collection])
    )

    if not collection_rows:
        print(f"[red]Error: Collection '{collection}' not found in database[/red]")
        return

    collection_id = collection_rows[0]["id"]

    # Get the chunk
    chunk_rows = list(
        db.query(
            "SELECT * FROM chunks WHERE id = ? AND collection_id = ?",
            [chunk_id, collection_id],
        )
    )

    if not chunk_rows:
        print(
            f"[red]Error: Chunk with ID '{chunk_id}' not found in collection '{collection}'[/red]"
        )
        return

    # Convert to dictionary
    chunk = dict(chunk_rows[0])
    chunk["metadata"] = json.loads(chunk["metadata"])

    # Display chunk details
    chunk_helpers.display_chunk(chunk, show_content)

    # Show ancestors if requested
    if show_ancestors:
        print("[blue]🌳 Chunk Ancestors:[/blue]")

        # Get all chunks to find ancestors
        all_chunks = list(
            db.query("SELECT * FROM chunks WHERE collection_id = ?", [collection_id])
        )

        # Convert to dictionaries
        all_chunk_dicts = []
        for row in all_chunks:
            chunk_dict = dict(row)
            chunk_dict["metadata"] = json.loads(chunk_dict["metadata"])
            all_chunk_dicts.append(chunk_dict)

        # Find ancestors
        ancestors = chunk_helpers.get_chunk_ancestors(all_chunk_dicts, chunk_id)

        if not ancestors:
            print("   [yellow]No ancestors found[/yellow]")
        else:
            for i, ancestor in enumerate(ancestors, 1):
                print(
                    f"   {i}. [cyan]{ancestor['type']}[/cyan]:[yellow]{ancestor['name']}[/yellow] "
                    f"({ancestor['path']}:{ancestor['start_line']}-{ancestor['end_line']})"
                )

    # Show children if requested
    if show_children:
        print("[blue]🌱 Chunk Children:[/blue]")

        # Get children directly from the database
        children = list(
            db.query(
                "SELECT * FROM chunks WHERE parent_id = ? AND collection_id = ?",
                [chunk_id, collection_id],
            )
        )

        # Convert to dictionaries
        child_chunks = []
        for row in children:
            child_dict = dict(row)
            child_dict["metadata"] = json.loads(child_dict["metadata"])
            child_chunks.append(child_dict)

        if not child_chunks:
            print("   [yellow]No children found[/yellow]")
        else:
            for i, child in enumerate(child_chunks, 1):
                print(
                    f"   {i}. [cyan]{child['type']}[/cyan]:[yellow]{child['name']}[/yellow] "
                    f"({child['path']}:{child['start_line']}-{child['end_line']})"
                )


@chunks.command()
@click.option("-d", "--dir", "project_dir", default=".", help="Project directory.")
@click.option(
    "-o",
    "--output",
    "output_dir",
    default=None,
    help="Output directory (default: .kaze in project directory).",
)
@click.option("-c", "--collection", default="chunks", help="Collection name.")
def stats(
    project_dir,
    output_dir,
    collection,
):
    """Show statistics about code chunks in the database."""
    project_dir = os.path.abspath(project_dir)
    kaze_dir = output_dir or os.path.join(project_dir, ".kaze")
    db_path = os.path.join(kaze_dir, "embeddings.db")

    if not os.path.exists(db_path):
        print(f"[red]Error: Embeddings database not found at [cyan]{db_path}[/cyan]")
        print(
            "Run [green]kaze chunks create[/green] first to generate chunk embeddings."
        )
        return

    # Connect to the database
    db = sqlite_utils.Database(db_path)

    # Check if collection exists
    if collection not in db_utils.list_collections(db):
        print(f"[red]Error: Collection '{collection}' not found in database[/red]")
        return

    print(f"[blue]📊 Chunk Statistics for Collection: [cyan]{collection}[/cyan]")

    try:
        # Get the collection ID
        collection_rows = list(
            db.query("SELECT id FROM collections WHERE name = ?", [collection])
        )

        if not collection_rows:
            print(f"[red]Error: Collection '{collection}' not found in database[/red]")
            return

        collection_id = collection_rows[0]["id"]

        # Get total chunk count
        total_rows = list(
            db.query(
                "SELECT COUNT(*) as count FROM chunks WHERE collection_id = ?",
                [collection_id],
            )
        )
        total_chunks = total_rows[0]["count"] if total_rows else 0

        print(f"[green]📈 Total Chunks: [yellow]{total_chunks}[/yellow]")

        # Count by type
        print("[green]📊 Chunks by Type:[/green]")
        type_counts = list(
            db.query(
                "SELECT type, COUNT(*) as count FROM chunks "
                "WHERE collection_id = ? GROUP BY type ORDER BY count DESC",
                [collection_id],
            )
        )

        for row in type_counts:
            print(f"   [cyan]{row['type']}[/cyan]: [yellow]{row['count']}[/yellow]")

        # Count by file (top 10)
        print("[green]📊 Files with Most Chunks (Top 10):[/green]")
        file_counts = list(
            db.query(
                "SELECT path, COUNT(*) as count FROM chunks "
                "WHERE collection_id = ? GROUP BY path ORDER BY count DESC LIMIT 10",
                [collection_id],
            )
        )

        for row in file_counts:
            print(f"   [blue]{row['path']}[/blue]: [yellow]{row['count']}[/yellow]")

        # Count top-level vs. nested chunks
        top_level_rows = list(
            db.query(
                "SELECT COUNT(*) as count FROM chunks "
                "WHERE collection_id = ? AND parent_id IS NULL",
                [collection_id],
            )
        )
        top_level_count = top_level_rows[0]["count"] if top_level_rows else 0

        nested_rows = list(
            db.query(
                "SELECT COUNT(*) as count FROM chunks "
                "WHERE collection_id = ? AND parent_id IS NOT NULL",
                [collection_id],
            )
        )
        nested_count = nested_rows[0]["count"] if nested_rows else 0

        print("[green]📊 Chunk Hierarchy:[/green]")
        print(f"   [cyan]Top-level chunks[/cyan]: [yellow]{top_level_count}[/yellow]")
        print(f"   [cyan]Nested chunks[/cyan]: [yellow]{nested_count}[/yellow]")

        # Nesting depth stats
        print("[green]📊 Nesting Depth:[/green]")

        # This requires recursive querying which is complex in SQLite
        # So we'll fetch all chunks and analyze in Python
        all_chunks = list(
            db.query(
                "SELECT id, parent_id FROM chunks WHERE collection_id = ?",
                [collection_id],
            )
        )

        # Build a lookup table to efficiently find parents
        chunk_by_id = {row["id"]: row for row in all_chunks}

        # Calculate depths
        depths = {}
        for chunk in all_chunks:
            depth = 0
            current = chunk
            while current.get("parent_id") and current["parent_id"] in chunk_by_id:
                depth += 1
                current = chunk_by_id[current["parent_id"]]

            if depth not in depths:
                depths[depth] = 0
            depths[depth] += 1

        # Display depth statistics
        for depth in sorted(depths.keys()):
            level_name = "Root level" if depth == 0 else f"Level {depth}"
            print(f"   [cyan]{level_name}[/cyan]: [yellow]{depths[depth]}[/yellow]")

    except Exception as e:
        print(f"[red]Error calculating chunk statistics: {str(e)}[/red]")


# Register with main CLI
if __name__ == "__main__":
    chunks()
