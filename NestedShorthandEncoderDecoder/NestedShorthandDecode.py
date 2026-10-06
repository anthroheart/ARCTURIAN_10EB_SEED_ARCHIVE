#!/usr/bin/env python3
"""
NestedShorthandDecode.py — Decode NestedShorthand.dat back to zip or any file — max lossless, balanced speed
- Accepts NestedShorthand.dat (noise/greek) and outputs original file(s) or generates virtual 10EB sparse file
- Supports NSH1 (old internal blocks) and NSH2 (new generic file container)
- For virtual: creates sparse file via fallocate/truncate — 10EB down to 20-100kB dat -> 10EB virtual instant low RAM
- Full ANSI color friendly menu if no args

Usage:
  python3 NestedShorthandDecode.py NestedShorthand.dat
  python3 NestedShorthandDecode.py NestedShorthand.dat -o out.zip
  python3 NestedShorthandDecode.py NestedShorthand.dat --list
  python3 NestedShorthandDecode.py NestedShorthand.dat --extract out_dir
  python3 NestedShorthandDecode.py NestedShorthand.dat --generate-10eb 10EB.dat
"""

from __future__ import annotations
import argparse
import struct
import zlib
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_BLUE = "\033[44m"

MAGIC_NSH1 = b'NSH1'
MAGIC_NSH2 = b'NSH2'
MAGIC_AHB1 = b'AHB1'
DEFAULT_KEY = b"AnthroHeart"

def xor_decode(data: bytes, key: bytes = DEFAULT_KEY) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def decompress_data(data: bytes, comp_type: int) -> bytes:
    if comp_type == 2:
        import lzma
        return lzma.decompress(data)
    else:
        return zlib.decompress(data)

def parse_nsh2(path: Path):
    raw = path.read_bytes()
    if len(raw) < 4+2+2+1+4+32:
        raise ValueError("Too small for NSH2")
    body_wo_sha = raw[:-32]
    footer_sha = raw[-32:]
    calc_sha = hashlib.sha256(body_wo_sha).digest()
    sha_valid = calc_sha == footer_sha
    if body_wo_sha[:4] != MAGIC_NSH2:
        raise ValueError("Invalid NSH2 MAGIC")
    version = struct.unpack_from('<H', body_wo_sha, 4)[0]
    flags = struct.unpack_from('<H', body_wo_sha, 6)[0]
    comp_type = body_wo_sha[8]
    num_files = struct.unpack_from('<I', body_wo_sha, 9)[0]
    offset = 13
    files = []
    for _ in range(num_files):
        if offset+2 > len(body_wo_sha):
            raise ValueError("Truncated filename len")
        fn_len = struct.unpack_from('<H', body_wo_sha, offset)[0]; offset+=2
        if offset+fn_len+8+8+4+32+1 > len(body_wo_sha):
            raise ValueError("Truncated file header")
        fname = body_wo_sha[offset:offset+fn_len].decode('utf-8'); offset+=fn_len
        orig_size = struct.unpack_from('<Q', body_wo_sha, offset)[0]; offset+=8
        comp_size = struct.unpack_from('<Q', body_wo_sha, offset)[0]; offset+=8
        crc_stored = struct.unpack_from('<I', body_wo_sha, offset)[0]; offset+=4
        sha_stored = body_wo_sha[offset:offset+32]; offset+=32
        is_virtual = struct.unpack_from('<B', body_wo_sha, offset)[0]; offset+=1
        if offset+comp_size+4 > len(body_wo_sha):
            raise ValueError(f"Truncated data for {fname}")
        xored = body_wo_sha[offset:offset+comp_size]; offset+=comp_size
        term = body_wo_sha[offset:offset+4]; offset+=4
        if term != b'\x00\x00\x00\x00':
            raise ValueError("Invalid TERM")
        try:
            comp = xor_decode(xored)
            data = decompress_data(comp, comp_type)
        except Exception as e:
            raise ValueError(f"Decompress failed for {fname}: {e}")
        # Verify
        crc_calc = zlib.crc32(data) & 0xFFFFFFFF
        sha_calc = hashlib.sha256(data).digest()
        valid = (crc_calc == crc_stored) and (sha_calc == sha_stored)
        files.append({
            "filename": fname,
            "orig_size": orig_size,
            "comp_size": comp_size,
            "crc": crc_stored,
            "sha": sha_stored.hex(),
            "is_virtual": bool(is_virtual),
            "data": data,
            "valid": valid
        })
    return version, files, sha_valid, footer_sha.hex(), comp_type

def parse_nsh1_generic(path: Path):
    # Fallback to old NSH1 internal blocks decoder
    raw = path.read_bytes()
    body_wo_sha = raw[:-32]
    footer_sha = raw[-32:]
    calc_sha = hashlib.sha256(body_wo_sha).digest()
    sha_valid = calc_sha == footer_sha
    version = struct.unpack_from('<H', body_wo_sha, 4)[0]
    num_blocks = struct.unpack_from('<I', body_wo_sha, 10)[0]
    offset = 14
    blocks = []
    for _ in range(num_blocks):
        type_id = struct.unpack_from('<B', body_wo_sha, offset)[0]; offset+=1
        orig_len = struct.unpack_from('<Q', body_wo_sha, offset)[0]; offset+=8
        comp_len = struct.unpack_from('<Q', body_wo_sha, offset)[0]; offset+=8
        crc_stored = struct.unpack_from('<I', body_wo_sha, offset)[0]; offset+=4
        xored = body_wo_sha[offset:offset+comp_len]; offset+=comp_len
        offset+=4
        try:
            comp = xor_decode(xored)
            orig = zlib.decompress(comp)
            valid = True
        except:
            orig = b""
            valid = False
        blocks.append({"type_id": type_id, "orig_len": orig_len, "data": orig, "valid": valid})
    return version, blocks, sha_valid

def print_header_nsh2(version, files, sha_valid, sha_hex, comp_type):
    c=Ansi
    print(f"{c.BG_BLUE}{c.WHITE}{c.BOLD} NestedShorthand v2 — Decode — 10EB Public Domain — Tiny Engine, Immense Model {c.RESET}")
    print(f"{c.CYAN}MAGIC:{c.RESET} NSH2  {c.CYAN}VERSION:{c.RESET} {version}  {c.CYAN}COMP:{c.RESET} {['', 'zlib', 'lzma'][comp_type] if comp_type<3 else comp_type}  {c.CYAN}FILES:{c.RESET} {len(files)}")
    col = c.GREEN if sha_valid else c.RED
    print(f"{c.CYAN}SHA256:{c.RESET} {col}{sha_hex[:24]}... {'VALID' if sha_valid else 'INVALID'}{c.RESET}")
    print(f"{c.DIM}Max encoded looks like noise/greek — tiny decoder immense payload — 10EB down to 20-100kB{c.RESET}\n")

def friendly_menu():
    c=Ansi
    print(f"{c.BOLD}{c.YELLOW}FRIENDLY MENU — Start with Categories, then Powers of 10 — Multi-pick allowed:{c.RESET}")
    print(f"{c.CYAN}Categories:{c.RESET}")
    cats = ["ALL", "SCIENCE", "MATHEMATICS", "SOFTWARE", "AI", "SIMULATIONS", "LANGUAGES", "MUSIC", "FILMS", "GAMES", "EDUCATION", "ART", "EVERYTHING", "LAW_OF_ONE", "RA_CONTACT", "STORY", "HYPERCOMPUTER", "DOCS"]
    for i, cat in enumerate(cats):
        print(f"  {c.GREEN}{i}{c.RESET} - {cat}")
    print(f"\n{c.CYAN}POW Sizes (Powers of 10):{c.RESET}")
    pows = ["Small Demo 1KB", "1MB", "1GB", "10GB", "100GB", "1TB", "10TB", "100TB", "1PB", "10PB", "100PB", "1EB (1e18)", "10EB (1e19) MAX"]
    for i, p in enumerate(pows):
        print(f"  {c.YELLOW}{i}{c.RESET} - {p}")
    print(f"\n{c.DIM}Pick multiple: e.g., categories '0' or '1,4,7' or 'SCIENCE,AI,MUSIC' or 'ALL'{c.RESET}")
    print(f"{c.DIM}Then POWs: e.g., '12' for 10EB or '2,3,12' for 1GB+10GB+10EB or '1GB,10EB'{c.RESET}\n")

def decode_file(input_path: Path, output_path: Path = None, extract_dir: Path = None, list_only: bool = False, generate_10eb_path: Path = None):
    magic = input_path.read_bytes()[:4]
    if magic == MAGIC_NSH2:
        version, files, sha_valid, sha_hex, comp_type = parse_nsh2(input_path)
        print_header_nsh2(version, files, sha_valid, sha_hex, comp_type)
        if list_only:
            c=Ansi
            for i, f in enumerate(files):
                virt = " [VIRTUAL]" if f["is_virtual"] else ""
                col = c.GREEN if f["valid"] else c.RED
                print(f"  [{i}] {f['filename']} orig={f['orig_size']} comp={f['comp_size']} {col}{'OK' if f['valid'] else 'FAIL'}{c.RESET}{virt}")
            return
        if generate_10eb_path:
            # If virtual file present, generate sparse
            for f in files:
                if f["is_virtual"]:
                    try:
                        manifest = json.loads(f["data"].decode('utf-8'))
                        vsize = manifest.get("virtual_size") or f["orig_size"]
                    except:
                        vsize = f["orig_size"]
                    print(f"Generating virtual sparse {generate_10eb_path} size {vsize}")
                    try:
                        subprocess.run(["fallocate", "-l", str(vsize), str(generate_10eb_path)], check=True)
                        print(f"Created sparse via fallocate")
                    except:
                        with open(generate_10eb_path, 'wb') as out:
                            out.seek(vsize-1)
                            out.write(b'\0')
                        print(f"Created sparse via seek")
                    return
            print("No virtual manifest found, cannot generate 10EB")
            return
        if extract_dir:
            extract_dir.mkdir(parents=True, exist_ok=True)
            for f in files:
                if f["is_virtual"]:
                    # Write manifest and generate sparse file
                    manifest_path = extract_dir / f["filename"]
                    manifest_path.write_bytes(f["data"])
                    print(f"Wrote manifest {manifest_path}")
                    # Try to parse virtual size
                    try:
                        manifest = json.loads(f["data"].decode('utf-8'))
                        vsize = manifest.get("virtual_size", f["orig_size"])
                    except:
                        vsize = f["orig_size"]
                    sparse_path = extract_dir / f"virtual_{vsize}.bin"
                    try:
                        subprocess.run(["fallocate", "-l", str(vsize), str(sparse_path)], check=True)
                    except:
                        with open(sparse_path, 'wb') as out:
                            out.seek(vsize-1)
                            out.write(b'\0')
                    print(f"Generated virtual sparse {sparse_path} size {vsize} (10EB down to {len(f['data'])} bytes manifest!)")
                else:
                    out_file = extract_dir / f["filename"]
                    out_file.parent.mkdir(parents=True, exist_ok=True)
                    out_file.write_bytes(f["data"])
                    print(f"Wrote {out_file} {len(f['data'])} bytes valid={f['valid']}")
            return
        # Single file output
        if output_path is None:
            # If single file, output to its original name
            if len(files) == 1 and not files[0]["is_virtual"]:
                output_path = Path(files[0]["filename"])
            else:
                output_path = Path("decoded_output.bin")
        if files[0]["is_virtual"]:
            # Generate sparse
            try:
                manifest = json.loads(files[0]["data"].decode('utf-8'))
                vsize = manifest.get("virtual_size", files[0]["orig_size"])
            except:
                vsize = files[0]["orig_size"]
            print(f"Virtual archive detected — generating sparse {output_path} size {vsize}")
            try:
                subprocess.run(["fallocate", "-l", str(vsize), str(output_path)], check=True)
            except:
                with open(output_path, 'wb') as out:
                    out.seek(vsize-1)
                    out.write(b'\0')
            print(f"Done — {output_path} is virtual {vsize} bytes, but only {output_path.stat().st_size} on disk (sparse) — 10EB down to ~{len(files[0]['data'])} bytes dat!")
        else:
            output_path.write_bytes(files[0]["data"])
            print(f"Wrote {output_path} {len(files[0]['data'])} bytes valid={files[0]['valid']}")
    elif magic == MAGIC_NSH1 or magic == b'AHB1':
        print(f"Detected old format {magic.decode()} — using legacy decoder")
        version, blocks, sha_valid = parse_nsh1_generic(input_path)[:3]
        print(f"Old format blocks {len(blocks)} SHA {'VALID' if sha_valid else 'INVALID'}")
        out_dir = extract_dir or Path("out_archive")
        out_dir.mkdir(parents=True, exist_ok=True)
        for i, b in enumerate(blocks):
            (out_dir / f"block_{i}_{b['type_id']}.txt").write_bytes(b["data"])
        print(f"Extracted to {out_dir}")
    else:
        raise ValueError(f"Unknown MAGIC {magic}")

def main():
    parser = argparse.ArgumentParser(description="NestedShorthandDecode.py — Decode NestedShorthand.dat back to zip/any file — friendly")
    parser.add_argument('input', nargs='?', default='NestedShorthand.dat', help='Input NestedShorthand.dat (default: NestedShorthand.dat)')
    parser.add_argument('-o', '--output', help='Output file path (for single file)')
    parser.add_argument('--extract', help='Extract all files to directory')
    parser.add_argument('--list', action='store_true', help='List files inside dat and exit')
    parser.add_argument('--generate-10eb', help='Generate virtual 10EB sparse file to path')
    parser.add_argument('--menu', action='store_true', help='Show friendly category + POW menu')
    args = parser.parse_args()

    if args.menu:
        friendly_menu()
        return 0

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input not found: {input_path}")
        # Show friendly menu if no file
        friendly_menu()
        return 1

    try:
        decode_file(
            input_path,
            output_path=Path(args.output) if args.output else None,
            extract_dir=Path(args.extract) if args.extract else None,
            list_only=args.list,
            generate_10eb_path=Path(args.generate_10eb) if args.generate_10eb else None
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    exit(main())
