import click
from kaze.core import db_utils
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
def info(project_dir, output_dir):
    """Show information about the embeddings database."""
    project_dir = os.path.abspath(project_dir)
    kaze_dir = output_dir or os.path.join(project_dir, ".kaze")
    db_path = os.path.join(kaze_dir, "embeddings.db")

    if not os.path.exists(db_path):
        print(f"[red]Error: Embeddings database not found at [cyan]{db_path}[/cyan]")
        print("Run [green]kaze create[/green] first to generate embeddings.")
        return

    print("[green]📊 Embeddings Database Information:[/green]")
    print("-------------------------------------------")
    print(f"[blue]📁 Database Path: [cyan]{db_path}[/cyan]")
    print(
        f"[blue]📏 Database Size: [yellow]{db_utils.get_db_size(db_path)}[/yellow][/blue]"
    )
    print("[blue]📚 Collections:[/blue]")
    print("[blue]📚 New Log:[/blue]")
    db_utils.show_collections(db_path)
    print("-------------------------------------------")
