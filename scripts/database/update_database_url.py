#!/usr/bin/env python3
"""Update DATABASE_URL in a local .env file.

Usage:
    python scripts/database/update_database_url.py "postgresql://user:pass@host/db?sslmode=require"

If no argument is provided, the script prompts for a URL. This script never
contains project-specific credentials; pass secrets at runtime instead.
"""
import getpass
import sys
from pathlib import Path


def update_database_url() -> bool:
    """Update DATABASE_URL in the first local .env file found."""
    new_db_url = sys.argv[1] if len(sys.argv) > 1 else getpass.getpass("New DATABASE_URL: ")
    if not new_db_url.strip():
        print("Error: DATABASE_URL cannot be empty.")
        return False

    project_root = Path(__file__).resolve().parents[2]
    env_paths = [project_root / ".env", project_root / "app" / ".env"]

    env_path = next((path for path in env_paths if path.exists()), None)
    if not env_path:
        print("Error: Could not find .env file.")
        return False

    original_content = env_path.read_text()
    lines = original_content.splitlines(keepends=True)

    updated = False
    for index, line in enumerate(lines):
        if line.startswith("DATABASE_URL="):
            lines[index] = f"DATABASE_URL={new_db_url}\n"
            updated = True
            break

    if not updated:
        lines.append(f"\nDATABASE_URL={new_db_url}\n")

    backup_path = env_path.with_suffix(env_path.suffix + ".backup")
    backup_path.write_text(original_content)
    env_path.write_text("".join(lines))

    print(f"Updated DATABASE_URL in {env_path}")
    print(f"Backup written to {backup_path}")
    return True


if __name__ == "__main__":
    sys.exit(0 if update_database_url() else 1)
