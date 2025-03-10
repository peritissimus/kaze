import llm
import os
from rich import print
import tiktoken


async def embed_file(file_path, model_name, db_path, collection_name):
    """Embed the context of file"""
    try:
        # Calculate the file ID (relative path)
        file_id = os.path.relpath(file_path, os.getcwd())

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Skip empty files
        if not content:
            print(f"[yellow]⚠️ Empty file: {file_path}[/yellow]")
            return True  # Consider it successful, nothing to do

        # Get the number of tokens for cost estimations

        num_tokens = num_tokens_from_string(content)

        print(
            f"[blue]Embedding the context from: {file_path}, {model_name}, tokens: {num_tokens}[/blue]"
        )

        # Embed the content using llm.embed
        await llm.embed(
            collection_name,
            file_id,
            model=model_name,
            content=content,
            database=db_path,
            store=True,
        )

        return True  # Success

    except Exception as e:
        print(f"[yellow]⚠️ Failed to embed {file_path}: {e}[/yellow]")
        return False  # Failure


def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens
