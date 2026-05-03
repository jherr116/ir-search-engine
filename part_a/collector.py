"""
collector.py - Bluesky Post Collector for IR Project (Part A)

Usage:
    python collector.py --max-posts 500000 --output-dir ../data

Description:
    Connects to the Bluesky API and collects posts matching a given query.
    Posts are stored as JSONL files (one post per line), rotated at ~10MB each.
    Posts containing external URLs are enriched with the linked page's title.
"""

import argparse
import json
import os
import time
import requests
from bs4 import BeautifulSoup
from atproto import Client


# ── Constants ────────────────────────────────────────────────────────────────
MAX_FILE_BYTES = 10 * 1024 * 1024   # 10 MB per file
REQUEST_DELAY  = 0.5                # seconds between API calls (be polite)

# ── Political Keywords ────────────────────────────────────────────────────────
POLITICAL_KEYWORDS = [
    "congress",
    "senate",
    "election",
    "trump",
    "democrat",
    "republican",
    "maga",
    "white house",
    "ballot",
    "supreme court",
    "tariff",
    "midterms",
    "political",
    "legislation",
    "impeach",
]


# ── URL Title Enrichment ─────────────────────────────────────────────────────
def get_page_title(url: str) -> str | None:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (IR-Project-Crawler/1.0)"}
        response = requests.get(url, timeout=5, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
    except Exception:
        pass
    return None


# ── Post Extraction ──────────────────────────────────────────────────────────
def extract_post_fields(post) -> dict:
    record = post.record

    linked_url   = None
    linked_title = None
    embed = getattr(record, "embed", None)
    try:
        if embed and embed.external:
            linked_url   = embed.external.uri
            linked_title = get_page_title(linked_url)
    except AttributeError:
        pass

    return {
        "uri":                  post.uri,
        "cid":                  post.cid,
        "author_handle":        post.author.handle,
        "author_display_name":  getattr(post.author, "display_name", ""),
        "text":                 record.text,
        "langs":                getattr(record, "langs", None) or [],
        "created_at":           record.created_at,
        "like_count":           getattr(post, "like_count",   None) or 0,
        "repost_count":         getattr(post, "repost_count", None) or 0,
        "reply_count":          getattr(post, "reply_count",  None) or 0,
        "linked_url":           linked_url,
        "linked_page_title":    linked_title,
    }


# ── File Rotation ────────────────────────────────────────────────────────────
class RotatingJSONLWriter:
    def __init__(self, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir   = output_dir
        self.file_index   = 1
        self.current_size = 0
        self.file         = None
        self._open_new_file()

    def _open_new_file(self):
        if self.file:
            self.file.close()
        path = os.path.join(self.output_dir, f"posts_{self.file_index:03}.jsonl")
        self.file         = open(path, "w", encoding="utf-8")
        self.current_size = 0
        print(f"  [writer] Opened {path}")

    def write(self, record: dict):
        line = json.dumps(record, ensure_ascii=False) + "\n"
        self.file.write(line)
        self.current_size += len(line.encode("utf-8"))
        if self.current_size >= MAX_FILE_BYTES:
            self.file_index += 1
            self._open_new_file()

    def close(self):
        if self.file:
            self.file.close()

    @property
    def files_written(self):
        return self.file_index


# ── Main Collection Logic ────────────────────────────────────────────────────
def collect(client, query: str, max_posts: int, output_dir: str,
            writer: RotatingJSONLWriter, seen_uris: set, total: int):
    """
    Collects posts for a single keyword.
    Takes shared client, writer, seen_uris, and total count from the outer loop.
    """
    print(f"\n  >> Searching: '{query}'")
    cursor    = None
    collected = 0

    while collected < max_posts:
        params = {"q": query, "limit": min(100, max_posts - collected)}
        if cursor:
            params["cursor"] = cursor

        response = None
        for attempt in range(5):
            try:
                response = client.app.bsky.feed.search_posts(params=params)
                break
            except Exception as error:
                print(f"  Network Timeout Occured, retrying again in {2 ** attempt}s...")
                time.sleep(2 ** attempt)
        else:
            print("  Still failed after five retry attempts, skipping page")
            break

        if not response.posts:
            print(f"  No more posts for '{query}'.")
            break

        for post in response.posts:
            if collected >= max_posts:
                break
            if post.uri in seen_uris:
                continue  # skip duplicate across keywords

            seen_uris.add(post.uri)
            record = extract_post_fields(post)
            writer.write(record)
            collected += 1
            total += 1

            if total % 100 == 0:
                print(f"  Collected {total} posts so far...")

        cursor = getattr(response, "cursor", None)
        if not cursor:
            print(f"  Reached end of results for '{query}'.")
            break

        time.sleep(REQUEST_DELAY)

    print(f"  Finished '{query}': {collected} new posts.")
    return total


# ── CLI Entry Point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bluesky post collector for IR project.")
    parser.add_argument("--max-posts",  type=int, default=500000, help="Total max posts to collect")
    parser.add_argument("--output-dir", default="../data", help="Directory to store JSONL files")
    parser.add_argument("--handle",     default=None, help="Bluesky handle (or set BSKY_HANDLE env var)")
    parser.add_argument("--password",   default=None, help="Bluesky app password (or set BSKY_PASSWORD env var)")
    args = parser.parse_args()

    handle   = args.handle   or os.environ.get("BSKY_HANDLE")
    password = args.password or os.environ.get("BSKY_PASSWORD")

    if not handle or not password:
        print("ERROR: Provide --handle and --password, or set BSKY_HANDLE / BSKY_PASSWORD env vars.")
        exit(1)

    # Log in once, reuse client for all keywords
    client = Client()
    client.login(handle, password)
    print(f"  Logged in as {handle}\n")

    # These are shared across all keyword runs
    writer    = RotatingJSONLWriter(args.output_dir)
    seen_uris = set()
    total     = 0

    posts_per_keyword = args.max_posts // len(POLITICAL_KEYWORDS)
    print(f"  Collecting {posts_per_keyword} posts per keyword across {len(POLITICAL_KEYWORDS)} keywords...\n")

    for keyword in POLITICAL_KEYWORDS:
        total = collect(
            client     = client,
            query      = keyword,
            max_posts  = posts_per_keyword,
            output_dir = args.output_dir,
            writer     = writer,
            seen_uris  = seen_uris,
            total      = total,
        )

    writer.close()
    print(f"\n  Done! Collected {total} total posts across {writer.files_written} file(s).")
    print(f"  Saved to: {os.path.abspath(args.output_dir)}\n")