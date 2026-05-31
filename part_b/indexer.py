"""
indexer.py - PyLucene Indexer for IR Project (Part B)

Usage:
    python indexer.py --data-dir ../data --index-dir ./index

Description:
    Reads all JSONL files from Part A and builds a PyLucene index.
    Indexes fields: text, author_handle, author_display_name,
                    created_at, like_count, repost_count, reply_count,
                    linked_page_title, uri
"""

import argparse
import glob
import json
import os
import sys
import time

import lucene
from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import (
    Document, Field, FieldType,
    StringField, TextField, StoredField, LongPoint, NumericDocValuesField
)
from org.apache.lucene.index import IndexWriter, IndexWriterConfig, IndexOptions
from org.apache.lucene.store import FSDirectory


# ── Field Type Helpers ────────────────────────────────────────────────────────

def make_stored_text_field():
    """Tokenized + stored — for fields you want to search AND display (e.g. post text)."""
    ft = FieldType()
    ft.setStored(True)
    ft.setTokenized(True)
    ft.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS)
    ft.freeze()
    return ft

def make_stored_meta_field():
    """NOT tokenized + stored — for fields you store but don't search (e.g. uri, timestamp)."""
    ft = FieldType()
    ft.setStored(True)
    ft.setTokenized(False)
    ft.setIndexOptions(IndexOptions.DOCS)
    ft.freeze()
    return ft


# ── Indexer ───────────────────────────────────────────────────────────────────

def build_index(data_dir: str, index_dir: str):
    """
    Reads all JSONL files from data_dir and writes a PyLucene index to index_dir.
    Each JSON line becomes one Lucene Document.
    """
    # Find all JSONL files
    files = sorted(glob.glob(os.path.join(data_dir, "*.jsonl")))
    if not files:
        print(f"ERROR: No .jsonl files found in {data_dir}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  PyLucene Indexer — Part B")
    print(f"  Data dir  : {data_dir}")
    print(f"  Index dir : {index_dir}")
    print(f"  Files     : {len(files)}")
    print(f"{'='*60}\n")

    # Initialize PyLucene JVM
    lucene.initVM(vmargs=["-Djava.awt.headless=true"])

    os.makedirs(index_dir, exist_ok=True)
    store    = FSDirectory.open(Paths.get(index_dir))
    analyzer = StandardAnalyzer()
    config   = IndexWriterConfig(analyzer)
    config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)  # overwrite existing index
    writer   = IndexWriter(store, config)

    # Field types (created once, reused for every document)
    TEXT_FIELD = make_stored_text_field()
    META_FIELD = make_stored_meta_field()

    total     = 0
    skipped   = 0
    start     = time.time()

    for path in files:
        print(f"  Indexing {os.path.basename(path)}...")
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    post = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue

                doc = Document()

                # --- Searchable text fields ---
                doc.add(Field("text",         str(post.get("text", "")),                TEXT_FIELD))
                doc.add(Field("author",       str(post.get("author_handle", "")),       TEXT_FIELD))
                doc.add(Field("display_name", str(post.get("author_display_name", "")), TEXT_FIELD))

                # Index linked page title if present (extra searchable text)
                linked_title = post.get("linked_page_title") or ""
                doc.add(Field("linked_title", linked_title, TEXT_FIELD))

                # --- Stored-only metadata fields (for display in results) ---
                doc.add(Field("uri",        str(post.get("uri", "")),        META_FIELD))
                doc.add(Field("created_at", str(post.get("created_at", "")), META_FIELD))
                doc.add(Field("linked_url", str(post.get("linked_url", "")), META_FIELD))

                # --- Numeric fields for combined ranking (stored + sortable) ---
                like_count    = int(post.get("like_count", 0)    or 0)
                repost_count  = int(post.get("repost_count", 0)  or 0)
                reply_count   = int(post.get("reply_count", 0)   or 0)

                # LongPoint makes them range-queryable; NumericDocValuesField makes them sortable
                doc.add(LongPoint("like_count",   like_count))
                doc.add(StoredField("like_count", like_count))
                doc.add(NumericDocValuesField("like_count_dv", like_count))

                doc.add(LongPoint("repost_count",   repost_count))
                doc.add(StoredField("repost_count", repost_count))

                doc.add(LongPoint("reply_count",   reply_count))
                doc.add(StoredField("reply_count", reply_count))

                writer.addDocument(doc)
                total += 1

                if total % 1000 == 0:
                    print(f"    Indexed {total:,} posts...")

    writer.commit()
    writer.close()

    elapsed = time.time() - start
    print(f"\n  Done!")
    print(f"  Indexed : {total:,} posts")
    print(f"  Skipped : {skipped} malformed lines")
    print(f"  Time    : {elapsed:.1f}s")
    print(f"  Index   : {os.path.abspath(index_dir)}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build PyLucene index from JSONL files.")
    parser.add_argument("--data-dir",  default="../data", help="Directory with .jsonl files from Part A")
    parser.add_argument("--index-dir", default="./index", help="Directory to write the Lucene index")
    args = parser.parse_args()

    build_index(args.data_dir, args.index_dir)
