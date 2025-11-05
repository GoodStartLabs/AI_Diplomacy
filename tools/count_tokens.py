#!/usr/bin/env python3
"""
Token counter utility for markdown files.
Uses tiktoken with cl100k_base encoding (GPT-4/Claude compatible).
"""

import sys
import os
from pathlib import Path
import tiktoken


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count tokens in text using specified encoding."""
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))


def process_file(file_path: Path) -> tuple[str, int, int]:
    """Process a single file and return stats."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    char_count = len(content)
    token_count = count_tokens(content)

    return file_path.name, char_count, token_count


def format_output(filename: str, char_count: int, token_count: int) -> str:
    """Format output line with stats."""
    ratio = token_count / char_count if char_count > 0 else 0
    return f"{filename}: {char_count:,} chars, {token_count:,} tokens ({ratio:.2f} tokens/char)"


def main():
    if len(sys.argv) < 2:
        print("Usage: count_tokens.py <file_or_directory>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"Error: {path} does not exist", file=sys.stderr)
        sys.exit(1)

    total_chars = 0
    total_tokens = 0

    # Collect files to process
    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(path.glob("*.md"))
        if not files:
            print(f"No .md files found in {path}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Error: {path} is neither a file nor directory", file=sys.stderr)
        sys.exit(1)

    # Process each file
    for file_path in files:
        try:
            filename, char_count, token_count = process_file(file_path)
            print(format_output(filename, char_count, token_count))
            total_chars += char_count
            total_tokens += token_count
        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)

    # Print total if multiple files
    if len(files) > 1:
        print(f"TOTAL: {total_chars:,} chars, {total_tokens:,} tokens")


if __name__ == "__main__":
    main()
