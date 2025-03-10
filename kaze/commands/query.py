import click
import json
from kaze.core import db_utils
from kaze.utils import display
import os
from rich import print


@click.command()
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
@click.option("-c", "--collection", default="files", help="Collection to search in.")
@click.option("--show-content", is_flag=True, help="Show file content in results.")
@click.option(
    "--human",
    "human_output",
    is_flag=True,
    help="Display human-readable output instead of JSON.",
)
def query(
    project_dir,
    output_dir,
    query_text,
    limit,
    threshold,
    collection,
    show_content,
    human_output,
):
    """Search for similar content across project files."""
    project_dir = os.path.abspath(project_dir)
    kaze_dir = output_dir or os.path.join(project_dir, ".kaze")
    db_path = os.path.join(kaze_dir, "embeddings.db")

    if not os.path.exists(db_path):
        if human_output:
            print(
                f"[red]Error: Embeddings database not found at [cyan]{db_path}[/cyan]"
            )
            print("Run [green]kaze create[/green] first to generate embeddings.")
        else:
            print(json.dumps({"error": "Database not found", "path": db_path}))
        return

    if human_output:
        print(f'[blue]🔍 Searching for: [cyan]"{query_text}"[/cyan]')
        print(f"[blue]📊 Using collection: [cyan]{collection}[/cyan]")
        print(f"[blue]📚 Maximum results: [cyan]{limit}[/cyan]")
        print(f"[blue]🎯 Similarity threshold: [cyan]{threshold}[/cyan]")

    results = db_utils.query_embeddings(
        db_path, collection, query_text, limit, threshold
    )

    if not results:
        if human_output:
            print("[yellow]⚠️ No results found matching your query.[/yellow]")
        else:
            print("[]")  # Empty JSON array
        return

    if human_output:
        display.display_human_results(results, project_dir, show_content)
    else:
        print(json.dumps(results))
