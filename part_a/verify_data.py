"""
verify_data.py - Quick sanity check on collected JSONL data

Run this after collection to confirm your data looks right before Part B.

Usage:
    python verify_data.py --data-dir ../data
"""

import argparse
import glob
import json
import os


def verify(data_dir: str):
    files = sorted(glob.glob(os.path.join(data_dir, "*.jsonl")))

    if not files:
        print(f"No .jsonl files found in {data_dir}")
        return

    total_posts      = 0
    total_bytes      = 0
    posts_with_links = 0
    fields_seen      = set()

    print(f"\n{'='*60}")
    print(f"  Data Verification — {data_dir}")
    print(f"{'='*60}\n")

    for path in files:
        size  = os.path.getsize(path)
        count = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    post = json.loads(line)
                    count += 1
                    fields_seen.update(post.keys())
                    if post.get("linked_page_title"):
                        posts_with_links += 1
                except json.JSONDecodeError:
                    print(f"  WARNING: Bad JSON line in {path}")

        print(f"  {os.path.basename(path):25s}  {count:>6} posts  {size/1e6:.2f} MB")
        total_posts += count
        total_bytes += size

    print(f"\n  {'─'*50}")
    print(f"  Total files  : {len(files)}")
    print(f"  Total posts  : {total_posts:,}")
    print(f"  Total size   : {total_bytes/1e6:.2f} MB  ({total_bytes/1e9:.3f} GB)")
    print(f"  Posts w/ URL : {posts_with_links:,} ({100*posts_with_links/max(total_posts,1):.1f}%)")
    print(f"\n  Fields present:")
    for f in sorted(fields_seen):
        print(f"    - {f}")

    # Sample the first post
    print(f"\n  Sample post (first record in first file):")
    with open(files[0], encoding="utf-8") as f:
        sample = json.loads(f.readline())
    for k, v in sample.items():
        print(f"    {k:25s}: {str(v)[:80]}")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify collected JSONL data.")
    parser.add_argument("--data-dir", default="../data", help="Directory containing .jsonl files")
    args = parser.parse_args()
    verify(args.data_dir)
