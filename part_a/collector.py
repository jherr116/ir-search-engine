"""
collector.py - Bluesky Post Collector for IR Project (Part A)

Usage:
    python collector.py --query "artificial intelligence" --max-posts 5000 --output-dir ../data

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


# ── URL Title Enrichment ─────────────────────────────────────────────────────
def get_page_title(url: str) -> str | None:
    """
    Fetch the <title> of a web page given its URL.
    Returns None if the request fails or no title is found.
    Required by the project spec: posts with embedded URLs must include the page title.
    """
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
    """
    Pull all fields from a Bluesky post object that we want to index in Part B.
    Returns a flat dictionary ready to be written as a JSON line.
    """
    record = post.record

    # Check for embedded external link (required by spec)
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
        # --- Identifiers ---
        "uri":                  post.uri,                          # unique document ID for PyLucene
        "cid":                  post.cid,

        # --- Author fields ---
        "author_handle":        post.author.handle,                # searchable username
        "author_display_name":  getattr(post.author, "display_name", ""),

        # --- Content fields ---
        "text":                 record.text,                       # main body — primary search field
        "langs":                getattr(record, "langs", []),

        # --- Temporal fields ---
        "created_at":           record.created_at,                 # ISO 8601 string

        # --- Engagement fields (for ranking in Part B) ---
        "like_count":           getattr(post, "like_count", 0),
        "repost_count":         getattr(post, "repost_count", 0),
        "reply_count":          getattr(post, "reply_count", 0),

        # --- Enriched URL fields (required by spec) ---
        "linked_url":           linked_url,
        "linked_page_title":    linked_title,                      # extra searchable text
    }


# ── File Rotation ────────────────────────────────────────────────────────────
class RotatingJSONLWriter:
    """
    Writes JSON lines to files, automatically opening a new file when the
    current one reaches MAX_FILE_BYTES (~10 MB), as required by the spec.
    """

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
def collect(query: str, max_posts: int, output_dir: str, handle: str, password: str):
    """
    Main collection loop.
    Paginates through Bluesky search results until max_posts is reached or
    the API has no more results.
    """
    print(f"\n{'='*60}")
    print(f"  Bluesky IR Collector — Part A")
    print(f"  Query     : {query}")
    print(f"  Max posts : {max_posts}")
    print(f"  Output    : {output_dir}")
    print(f"{'='*60}\n")

    # Log in
    client = Client()
    client.login(handle, password)
    print(f"  Logged in as {handle}\n")

    writer     = RotatingJSONLWriter(output_dir)
    total      = 0
    cursor     = None
    seen_uris  = set()  # deduplication

    try:
        while total < max_posts:
            params = {"q": query, "limit": min(100, max_posts - total)}
            if cursor:
                params["cursor"] = cursor

            response = client.app.bsky.feed.search_posts(params=params)

            if not response.posts:
                print("  No more posts returned by API.")
                break

            for post in response.posts:
                if total >= max_posts:
                    break
                if post.uri in seen_uris:
                    continue

                seen_uris.add(post.uri)
                record = extract_post_fields(post)
                writer.write(record)
                total += 1

                if total % 100 == 0:
                    print(f"  Collected {total} posts so far...")

            cursor = getattr(response, "cursor", None)
            if not cursor:
                print("  Reached end of results (no more cursor).")
                break

            time.sleep(REQUEST_DELAY)

    finally:
        writer.close()

    print(f"\n  Done! Collected {total} posts across {writer.files_written} file(s).")
    print(f"  Saved to: {os.path.abspath(output_dir)}\n")


# ── CLI Entry Point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bluesky post collector for IR project.")
    parser.add_argument("--query",      required=True,  help="Search keyword(s), e.g. 'climate change'")
    parser.add_argument("--max-posts",  type=int, default=5000, help="Max number of posts to collect")
    parser.add_argument("--output-dir", default="../data", help="Directory to store JSONL files")
    parser.add_argument("--handle",     default=None, help="Bluesky handle (or set BSKY_HANDLE env var)")
    parser.add_argument("--password",   default=None, help="Bluesky app password (or set BSKY_PASSWORD env var)")
    args = parser.parse_args()

    handle   = args.handle   or os.environ.get("BSKY_HANDLE")
    password = args.password or os.environ.get("BSKY_PASSWORD")

    if not handle or not password:
        print("ERROR: Provide --handle and --password, or set BSKY_HANDLE / BSKY_PASSWORD env vars.")
        exit(1)

    collect(
        query      = args.query,
        max_posts  = args.max_posts,
        output_dir = args.output_dir,
        handle     = handle,
        password   = password,
    )
