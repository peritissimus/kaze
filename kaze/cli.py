import click
from kaze.commands import create, query, info
from kaze.utils import config


@click.group()
@click.pass_context
def cli(ctx):
    """
    Kaze: Unified tool for creating and querying embeddings for project files.
    """
    # Initialize configuration (or load from file) here if needed
    ctx.ensure_object(dict)  # Ensure there's a context object


cli.add_command(create.create)
cli.add_command(query.query)
cli.add_command(info.info)

if __name__ == "__main__":
    cli()
