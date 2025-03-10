from rich import print
import os


def display_human_results(results, project_dir, show_content):
    """Displays search results in a human-readable format."""
    print("[green]📋 Search results:[/green]")
    print("-------------------------------------------")

    for result in results:
        file_id = result["id"]
        score = result["score"]
        content = result["content"]
        metadata = result["metadata"]

        # Format score as percentage
        score_percent = round(score * 100, 1)

        # Get file path
        file_path = file_id
        if not os.path.exists(file_path) and os.path.exists(
            os.path.join(project_dir, file_id)
        ):
            file_path = os.path.join(project_dir, file_id)

        print(f"[cyan]{file_id}[/cyan] ([yellow]{score_percent}%[/yellow] match)")

        if show_content:
            # Show content if available
            if content:
                print("[purple]--- Content Preview:[/purple]")
                print(content[:200])  # Show a snippet of the content
                print("[purple]...[/purple]")  # Indicate truncation
                print("[purple]-------------------[/purple]")
            elif os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_content = f.read()
                        print("[purple]--- File Preview:[/purple]")
                        print(file_content[:200])
                        print("[purple]...[/purple]")
                        print("[purple]-------------------[/purple]")
                except Exception as e:
                    print(f"[yellow]⚠️ Error reading file {file_path}: {e}[/yellow]")

            # Show metadata if available
            if metadata and metadata != {}:
                print(f"[blue]Metadata:[/blue] {metadata}")

    print("-------------------------------------------")
    print("[green]🎉 Search complete![/green]")
