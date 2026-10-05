#!/usr/bin/env python3
"""
Generate 10 cryptographic hashes for a file and append them to a
.hash archival record containing an official UTC timestamp.

Usage:
    python archive_hash.py /path/to/file
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ALGORITHMS = [
    "md5",
    "sha1",
    "sha224",
    "sha256",
    "sha384",
    "sha512",
    "sha3_224",
    "sha3_256",
    "sha3_384",
    "sha3_512",
]

CHUNK_SIZE = 1024 * 1024  # 1 MiB


def hash_file(path: Path) -> dict:
    hashes = {name: hashlib.new(name) for name in ALGORITHMS}

    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            for h in hashes.values():
                h.update(chunk)

    return {name: h.hexdigest() for name, h in hashes.items()}


def create_record(file_path: Path) -> dict:
    stat = file_path.stat()

    return {
        "file": file_path.name,
        "absolute_path": str(file_path.resolve()),
        "size_bytes": stat.st_size,
        "modified_timestamp_utc": datetime.fromtimestamp(
            stat.st_mtime, timezone.utc
        ).isoformat(),
        "archival_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hashes": hash_file(file_path),
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.is_file():
        print(f"Error: file not found: {file_path}")
        sys.exit(1)

    record = create_record(file_path)

    # Append to: original_filename.hash
    hash_file_path = file_path.with_name(file_path.name + ".hash")

    with hash_file_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, indent=2))
        f.write("\n" + "=" * 80 + "\n")

    print(f"Archived hashes: {hash_file_path}")
    print(f"UTC timestamp:   {record['archival_timestamp_utc']}")


if __name__ == "__main__":
    main()

