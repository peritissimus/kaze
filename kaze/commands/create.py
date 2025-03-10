import click
from kaze.core import file_utils, embedding_utils, db_utils
from kaze.utils import config
import os
from rich import print
import tiktoken
import asyncio


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
@click.option("-s", "--size", default=8, type=int, help="Maximum file size in KB.")
@click.option("-b", "--batch", default=10, type=int, help="Batch size for processing.")
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
):
    """Create embeddings for files in the project."""

    project_dir = os.path.abspath(project_dir)
    kaze_dir = output_dir or os.path.join(project_dir, ".kaze")
    db_path = os.path.join(kaze_dir, "embeddings.db")

    print(f"[blue]🔍 Processing files in [cyan]{project_dir}[/cyan]")
    print(f"[blue]💾 Embeddings will be saved to [cyan]{db_path}[/cyan]")
    print(f"[blue]🧠 Using model: [cyan]{model}[/cyan]")

    os.makedirs(kaze_dir, exist_ok=True)

    if force and os.path.exists(db_path):
        print("[yellow]⚠️ Force flag set - removing existing database[/yellow]")
        os.remove(db_path)
    elif os.path.exists(db_path):
        print(f"[yellow]⚠️ Embeddings database already exists at [cyan]{db_path}[/cyan]")
        print("   Use [green]--force[/green] to recreate the database")
        return

    file_list = file_utils.get_file_list(project_dir, include_pattern, exclude_pattern)

    if not file_list:
        print("[yellow]⚠️ No suitable files found to process[/yellow]")
        return

    print(f"[green]📊 Found [yellow]{len(file_list)}[/yellow] files to process[/green]")

    # Process files and create embeddings
    success_count = 0
    fail_count = 0

    # Async Embedding Process
    async def embed_all_files(file_list):
        tasks = [
            asyncio.create_task(
                embedding_utils.embed_file(file, model, db_path, collection)
            )
            for file in file_list
        ]
        results = await asyncio.gather(*tasks)
        return results

    results = asyncio.run(embed_all_files(file_list))

    success_count = results.count(True)
    fail_count = results.count(False)

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
