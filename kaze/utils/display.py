from rich import print
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import os


def display_human_results(results, project_dir, show_content, context_lines=None):
    """Displays search results in a human-readable format."""
    print("[green]📋 Search results:[/green]")
    print("-------------------------------------------")

    for idx, result in enumerate(results, 1):
        file_id = result["id"]
        score = result["score"]
        content = result["content"]
        metadata = result["metadata"]

        # Format score as percentage
        score_percent = round(score * 100, 1)

        # Get absolute file path
        file_path = file_id
        if not os.path.exists(file_path) and os.path.exists(
            os.path.join(project_dir, file_id)
        ):
            file_path = os.path.join(project_dir, file_id)

        # Determine the file language for syntax highlighting
        file_extension = os.path.splitext(file_path)[1].lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".md": "markdown",
            ".sh": "bash",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".go": "go",
            ".rb": "ruby",
            ".rs": "rust",
            ".ts": "typescript",
            ".sql": "sql",
            ".php": "php",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".xml": "xml",
        }
        language = language_map.get(file_extension, "text")

        # Create a panel for the result
        header = (
            f"[{idx}] [cyan]{file_id}[/cyan] ([yellow]{score_percent}%[/yellow] match)"
        )
        if metadata and metadata.get("tokens"):
            header += f" - [blue]{metadata.get('tokens')}[/blue] tokens"

        print(Panel(header, title="Result", expand=False))

        if show_content:
            # Show content if available
            if content:
                if context_lines is not None:
                    # Try to find the most relevant part of the file
                    # This is a simple approach - in a real implementation, you would
                    # use more sophisticated methods to identify the most relevant context
                    lines = content.split("\n")
                    if len(lines) > context_lines * 2:
                        # Find a middle segment that's most likely to be relevant
                        middle = len(lines) // 2
                        start = max(0, middle - context_lines)
                        end = min(len(lines), middle + context_lines)
                        context_content = "\n".join(lines[start:end])
                        print(
                            Syntax(
                                context_content,
                                language,
                                line_numbers=True,
                                start_line=start + 1,
                            )
                        )
                    else:
                        # File is short enough to show in full
                        print(Syntax(content, language, line_numbers=True))
                else:
                    # Show a snippet of the content
                    print(Syntax(content[:500], language))
                    if len(content) > 500:
                        print("[purple]...(truncated)[/purple]")
            elif os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_content = f.read()
                        if context_lines is not None:
                            lines = file_content.split("\n")
                            if len(lines) > context_lines * 2:
                                middle = len(lines) // 2
                                start = max(0, middle - context_lines)
                                end = min(len(lines), middle + context_lines)
                                context_content = "\n".join(lines[start:end])
                                print(
                                    Syntax(
                                        context_content,
                                        language,
                                        line_numbers=True,
                                        start_line=start + 1,
                                    )
                                )
                            else:
                                print(Syntax(file_content, language, line_numbers=True))
                        else:
                            print(Syntax(file_content[:500], language))
                            if len(file_content) > 500:
                                print("[purple]...(truncated)[/purple]")
                except Exception as e:
                    print(f"[yellow]⚠️ Error reading file {file_path}: {e}[/yellow]")

            # Show metadata if available
            if metadata and metadata != {}:
                # Create a table for metadata
                table = Table(title="Metadata")
                table.add_column("Key", style="cyan")
                table.add_column("Value", style="yellow")

                for key, value in metadata.items():
                    table.add_row(str(key), str(value))

                print(table)

        print("-------------------------------------------")

    print(f"[green]🎉 Found {len(results)} matching results![/green]")


def display_file_preview(file_path, max_lines=20):
    """Display a preview of a file with syntax highlighting."""
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".md": "markdown",
            ".sh": "bash",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".go": "go",
            ".rb": "ruby",
            ".rs": "rust",
            ".ts": "typescript",
            ".sql": "sql",
            ".php": "php",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".xml": "xml",
        }
        language = language_map.get(file_extension, "text")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        lines = content.split("\n")
        if len(lines) > max_lines:
            preview = "\n".join(lines[:max_lines])
            preview += f"\n... ({len(lines) - max_lines} more lines)"
        else:
            preview = content

        print(Syntax(preview, language, line_numbers=True))
    except Exception as e:
        print(f"[yellow]⚠️ Error displaying file preview: {e}[/yellow]")
