import click
import llm
from kaze.core import file_utils, embedding_utils, db_utils
from kaze.utils import config
import os
from rich import print
import asyncio
import sqlite_utils


@click.command()
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
@click.option("-b", "--batch", default=20, type=int, help="Batch size for processing.")
@click.option("-c", "--collection", default="files", help="Collection name.")
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
    "--verify",
    is_flag=True,
    help="Verify embedding model is available.",
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
    verify,
):
    """Create embeddings for files in the project."""

    project_dir = os.path.abspath(project_dir)
    kaze_dir = output_dir or os.path.join(project_dir, ".kaze")
    db_path = os.path.join(kaze_dir, "embeddings.db")

    print(f"[blue]🔍 Processing files in [cyan]{project_dir}[/cyan]")
    print(f"[blue]💾 Embeddings will be saved to [cyan]{db_path}[/cyan]")
    print(f"[blue]🧠 Using model: [cyan]{model}[/cyan]")

    # Verify the embedding model
    if verify:
        try:
            print(f"[blue]🔍 Verifying embedding model: [cyan]{model}[/cyan]")
            embedding_model = llm.get_embedding_model(model)
            print(f"[green]✅ Model verified: [cyan]{embedding_model.model_id}[/cyan]")
        except Exception as e:
            print(f"[red]❌ Error: Could not load embedding model '{model}': {e}[/red]")
            return

    os.makedirs(kaze_dir, exist_ok=True)

    # Initialize the database
    db = sqlite_utils.Database(db_path)

    # Handle force flag
    if force and os.path.exists(db_path):
        print("[yellow]⚠️ Force flag set - removing existing database[/yellow]")
        os.remove(db_path)
        db = sqlite_utils.Database(db_path)  # Reconnect to the new DB
    elif os.path.exists(db_path):
        # Check if collection exists
        try:
            if collection in db_utils.list_collections(db):
                print(f"[yellow]⚠️ Collection '{collection}' already exists in database")
                print(
                    "   Use [green]--force[/green] to recreate the collection[/yellow]"
                )
                return
        except Exception as e:
            print(f"[yellow]⚠️ Error checking collections: {e}[/yellow]")
            print("   Continuing with database creation")

    # Get file list
    file_list = file_utils.get_file_list(project_dir, include_pattern, exclude_pattern)

    # Update should_process_file max size from parameter
    file_utils.should_process_file.max_file_size_kb = size

    if not file_list:
        print("[yellow]⚠️ No suitable files found to process[/yellow]")
        return

    print(f"[green]📊 Found [yellow]{len(file_list)}[/yellow] files to process[/green]")

    # Process files in batches using async
    async def process_files():
        results = await embedding_utils.embed_files_batch(
            file_list, model, db_path, collection, batch
        )
        return results

    # Run the async batch processing
    results = asyncio.run(process_files())

    # Count successes and failures
    success_count = results.count(True) if results else 0
    fail_count = len(results) - success_count if results else 0

    print(
        f"\n[green]Processing complete! Successfully processed [yellow]{success_count}[/yellow] files, failed to process [yellow]{fail_count}[/yellow] files.[/green]"
    )

    if os.path.exists(db_path):
        print(
            f"[green]✅ Embeddings successfully created and saved to [cyan]{db_path}[/cyan]"
        )
        print(
            f"[green]🔢 Database size: [yellow]{file_utils.get_file_size(db_path)}[/yellow][/green]"
        )
        print("[green]📚 Collections in database:[/green]")
        db_utils.show_collections(db_path)
    else:
        print("[red]❌ Error: Failed to create embeddings database[/red]")

    print("[green]🎉 All done![/green]")
