#!/usr/bin/env python
"""Run database migrations"""
import subprocess
import sys
from pathlib import Path


def main():
    """Run alembic migrations"""
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Migration failed: {result.stderr}")
        sys.exit(1)

    print("Migrations completed successfully")
    print(result.stdout)


if __name__ == "__main__":
    main()