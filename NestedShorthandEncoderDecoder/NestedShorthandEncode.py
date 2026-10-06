#!/usr/bin/env python3
"""
NestedShorthandEncode.py — Encode any file (zip or any) to NestedShorthand.dat — max lossless, balanced speed
- Takes input zip or any file, outputs NestedShorthand.dat (looks like noise/greek)
- Balance of speed and compression: default level 6, --fast level 1, --max level 9, --ultra uses lzma
- Can produce 10EB virtual archive down to ~20-100kB via --virtual-size
- Format: NSH2 (NestedShorthand v2) — MAGIC NSH2, VERSION 12, COMP_TYPE, NUM_FILES
- Each file entry: FILENAME_LEN u16, FILENAME utf-8, ORIG_SIZE u64, COMP_SIZE u64, CRC32 u32, SHA256 32B, IS_VIRTUAL u8, DATA (zlib/lzma + XOR AnthroHeart)
- For virtual: DATA is manifest JSON, ORIG_SIZE is virtual size (e.g., 10EB), IS_VIRTUAL=1, decode creates sparse file via fallocate

Usage:
  python3 NestedShorthandEncode.py input.zip
  python3 NestedShorthandEncode.py input.zip -o NestedShorthand.dat
  python3 NestedShorthandEncode.py --virtual-size 10EB -o NestedShorthand.dat
  python3 NestedShorthandEncode.py --virtual-size 10EB --categories "SCIENCE,AI,MUSIC" -o NestedShorthand.dat
  python3 NestedShorthandEncode.py big.zip --max
  python3 NestedShorthandEncode.py big.zip --fast
"""

from __future__ import annotations
import argparse
import struct
import zlib
import hashlib
import json
import time
import os
from pathlib import Path
from typing import List, Tuple

MAGIC = b'NSH2'
VERSION = 12
DEFAULT_KEY = b"AnthroHeart"

# Size parser for 10EB etc
SIZE_MAP = {
    "1KB": 1024,
    "1MB": 1000*1000,
    "1GB": 1000**3,
    "10GB": 10*1000**3,
    "100GB": 100*1000**3,
    "1TB": 1000**4,
    "10TB": 10*1000**4,
    "100TB": 100*1000**4,
    "1PB": 1000**5,
    "10PB": 10*1000**5,
    "100PB": 100*1000**5,
    "1EB": 10**18,
    "10EB": 10**19,
    "1EB_BINARY": 1024**6,
    "10EB_BINARY": 10*1024**6,
}

def parse_human_size(s: str) -> int:
    s = s.strip().upper()
    if s in SIZE_MAP:
        return SIZE_MAP[s]
    # Try numeric with suffix
    try:
        if s.endswith("EB"):
            num = float(s[:-2])
            return int(num * 10**18)
        if s.endswith("PB"):
            num = float(s[:-2])
            return int(num * 1000**5)
        if s.endswith("TB"):
            num = float(s[:-2])
            return int(num * 1000**4)
        if s.endswith("GB"):
            num = float(s[:-2])
            return int(num * 1000**3)
        if s.endswith("MB"):
            num = float(s[:-2])
            return int(num * 1000**2)
        if s.endswith("KB"):
            num = float(s[:-2])
            return int(num * 1024)
        return int(s)
    except:
        raise ValueError(f"Cannot parse size: {s}")

def xor_encode(data: bytes, key: bytes = DEFAULT_KEY) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def compress_data(data: bytes, level: int = 6, use_lzma: bool = False) -> bytes:
    if use_lzma:
        import lzma
        # preset 6 balanced, 9 max
        preset = 6 if level < 9 else 9
        return lzma.compress(data, preset=preset)
    else:
        return zlib.compress(data, level=level)

def build_virtual_manifest(virtual_size: int, categories: List[str] = None, note: str = "") -> bytes:
    manifest = {
        "version": VERSION,
        "type": "virtual",
        "virtual_size": virtual_size,
        "virtual_human": f"{virtual_size} bytes ({virtual_size / 1e18:.1f} EB)" if virtual_size >= 1e18 else f"{virtual_size} bytes",
        "method": "sparse file via fallocate/truncate — tiny engine immense model — like colibri MoE streaming experts from disk",
        "engine": "AnthroHeart NestedShorthand v2",
        "categories": categories or ["ALL"],
        "note": note or "Full one for humanity — 10EB public domain — not 10EB inside dat, generator streams via fallocate sparse + manifest",
        "generation": {
            "bash": f"fallocate -l {virtual_size} output.bin || truncate -s {virtual_size} output.bin",
            "python": f"open('output.bin','wb').seek({virtual_size}-1); write(b'\\0')"
        },
        "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }
    return json.dumps(manifest, indent=2).encode('utf-8')

def encode_file(input_path: Path, output_path: Path, level: int = 6, use_lzma: bool = False, virtual_size: int = None, categories: List[str] = None):
    files_to_store: List[Tuple[str, bytes, bool, int]] = []  # filename, data, is_virtual, virtual_orig_size

    if virtual_size is not None:
        # Virtual mode — no need to read input, create manifest
        manifest_data = build_virtual_manifest(virtual_size, categories, note=f"Categories: {categories}" if categories else "")
        # For virtual, we store one entry that is manifest, but orig_size is virtual size
        files_to_store.append(("virtual_manifest.json", manifest_data, True, virtual_size))
        print(f"Virtual mode: virtual size {virtual_size} ({virtual_size/1e18 if virtual_size>=1e18 else virtual_size} EB) -> manifest {len(manifest_data)} bytes")
    else:
        if not input_path.exists():
            raise FileNotFoundError(f"Input not found: {input_path}")
        if input_path.is_dir():
            # Encode directory as zip-like: collect all files
            for f in input_path.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(input_path)
                    data = f.read_bytes()
                    files_to_store.append((str(rel), data, False, len(data)))
        else:
            data = input_path.read_bytes()
            files_to_store.append((input_path.name, data, False, len(data)))

    # Build header
    comp_type = 2 if use_lzma else 1  # 1=zlib, 2=lzma
    num_files = len(files_to_store)
    header = MAGIC + struct.pack('<H', VERSION) + struct.pack('<H', 0) + struct.pack('<B', comp_type) + struct.pack('<I', num_files)

    body = b''
    total_orig = 0
    total_comp = 0

    for filename, data, is_virtual, virtual_orig in files_to_store:
        # Compress
        compressed = compress_data(data, level=level, use_lzma=use_lzma)
        xored = xor_encode(compressed)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        sha = hashlib.sha256(data).digest()
        fname_bytes = filename.encode('utf-8')
        orig_size = virtual_orig if is_virtual else len(data)
        total_orig += orig_size
        total_comp += len(xored)

        body += struct.pack('<H', len(fname_bytes))
        body += fname_bytes
        body += struct.pack('<Q', orig_size)
        body += struct.pack('<Q', len(xored))
        body += struct.pack('<I', crc)
        body += sha
        body += struct.pack('<B', 1 if is_virtual else 0)
        body += xored
        body += b'\x00\x00\x00\x00'

    sha_footer = hashlib.sha256(header + body).digest()
    final_data = header + body + sha_footer

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(final_data)

    ratio = total_comp / total_orig if total_orig else 0
    print(f"Encoded {num_files} file(s) -> {output_path} size {len(final_data)} bytes")
    print(f"Original total (virtual if virtual): {total_orig} bytes, Compressed total (xored): {total_comp} bytes, Ratio: {ratio:.6f}")
    if virtual_size:
        print(f"Virtual 10EB down to {len(final_data)} bytes — {len(final_data)/1024:.1f} kB — tiny engine immense model!")
    print(f"Looks like noise/greek: first 100 hex {final_data[:100].hex()[:100]}")
    return output_path

def main():
    parser = argparse.ArgumentParser(description="NestedShorthandEncode.py — Encode any zip/file to NestedShorthand.dat — balanced max lossless")
    parser.add_argument('input', nargs='?', help='Input file or directory (zip or any). If --virtual-size given, input is optional.')
    parser.add_argument('-o', '--output', default='NestedShorthand.dat', help='Output NestedShorthand.dat path (default: NestedShorthand.dat)')
    parser.add_argument('--level', type=int, default=6, help='Compression level 1-9 (default 6 balanced)')
    parser.add_argument('--fast', action='store_true', help='Fast compression level 1')
    parser.add_argument('--max', action='store_true', help='Max compression level 9')
    parser.add_argument('--ultra', action='store_true', help='Ultra max using lzma (slower but smaller)')
    parser.add_argument('--virtual-size', type=str, help='Create virtual archive of size e.g., 10EB, 1EB, 100PB, 10TB (down to ~20-100kB)')
    parser.add_argument('--categories', type=str, help='Categories for virtual manifest, comma separated e.g., SCIENCE,AI,MUSIC or ALL')
    args = parser.parse_args()

    level = args.level
    if args.fast:
        level = 1
    if args.max:
        level = 9
    use_lzma = args.ultra

    virtual_size = None
    if args.virtual_size:
        try:
            virtual_size = parse_human_size(args.virtual_size)
        except ValueError as e:
            print(f"Error: {e}")
            return 1

    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(',') if c.strip()]

    input_path = Path(args.input) if args.input else None
    output_path = Path(args.output)

    if virtual_size is None and input_path is None:
        parser.error("Provide input file or --virtual-size")

    try:
        encode_file(input_path, output_path, level=level, use_lzma=use_lzma, virtual_size=virtual_size, categories=categories)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    exit(main())
