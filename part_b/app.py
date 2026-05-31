"""
app.py - Flask Search Interface for IR Project (Part B)

Usage:
    python app.py --index-dir ./index
    Then open http://localhost:5000 in your browser.

Description:
    Flask web app that searches the PyLucene index built by indexer.py.
    Supports:
      - Full-text search over post text, author, and linked page titles
      - Combined ranking: PyLucene score + likes + recency (extra credit)
      - Custom snippet generation with query term highlighting (extra credit)
      - Sort modes: relevance, combined, likes, newest
"""

import argparse
import math
import os
import re
from datetime import datetime, timezone

import lucene
from flask import Flask, render_template, request
from java.nio.file import Paths
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import MultiFieldQueryParser, QueryParser
from org.apache.lucene.search import IndexSearcher, BooleanQuery
from org.apache.lucene.store import FSDirectory


app = Flask(__name__)

# Global searcher — initialized once at startup
_searcher  = None
_analyzer  = None
_index_dir = None

RESULTS_PER_PAGE = 10


# ── PyLucene Setup ────────────────────────────────────────────────────────────

def init_lucene(index_dir: str):
    global _searcher, _analyzer, _index_dir
    lucene.initVM(vmargs=["-Djava.awt.headless=true"])
    store     = FSDirectory.open(Paths.get(index_dir))
    reader    = DirectoryReader.open(store)
    _searcher = IndexSearcher(reader)
    _analyzer = StandardAnalyzer()
    _index_dir = index_dir
    print(f"  Loaded index: {index_dir} ({reader.numDocs():,} documents)")


# ── Snippet Generation (Extra Credit) ────────────────────────────────────────

def generate_snippet(text: str, query_terms: list[str], max_len: int = 200) -> str:
    """
    Custom snippet generator — finds the sentence with the most query term
    hits and returns it with terms wrapped in <mark> tags.
    Does NOT use PyLucene's built-in highlighter (as required by spec).
    """
    if not text:
        return ""

    query_terms_lower = [t.lower() for t in query_terms if len(t) > 2]

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Score each sentence by how many unique query terms it contains
    best_sentence = text[:max_len]
    best_score    = 0

    for sentence in sentences:
        sentence_lower = sentence.lower()
        score = sum(1 for term in query_terms_lower if term in sentence_lower)
        if score > best_score:
            best_score    = score
            best_sentence = sentence

    # Truncate if still too long
    snippet = best_sentence[:max_len]
    if len(best_sentence) > max_len:
        snippet += "..."

    # Highlight query terms with <mark> tags
    for term in query_terms_lower:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        snippet = pattern.sub(lambda m: f"<mark>{m.group()}</mark>", snippet)

    return snippet


# ── Combined Ranking Score (Extra Credit) ────────────────────────────────────

def combined_score(
    lucene_score: float,
    like_count: int,
    created_at: str,
    w_relevance: float = 0.6,
    w_likes: float = 0.25,
    w_recency: float = 0.15,
    max_likes: int = 10000,
) -> float:
    """
    Combines three signals into one final ranking score:
      - Relevance : PyLucene's BM25 score (normalized)
      - Popularity: like_count (log-normalized so viral posts don't dominate)
      - Recency   : exponential decay — posts lose score as they age

    Weights sum to 1.0 and are adjustable via the UI.
    """
    # Normalize relevance (PyLucene scores are typically 0–20)
    norm_relevance = min(lucene_score / 20.0, 1.0)

    # Log-normalize likes so a post with 10k likes isn't 1000x better than 10 likes
    norm_likes = math.log1p(like_count) / math.log1p(max(max_likes, 1))
    norm_likes = min(norm_likes, 1.0)

    # Recency: exponential decay with 30-day half-life
    norm_recency = 0.5  # default if date is missing
    try:
        post_dt  = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now      = datetime.now(timezone.utc)
        age_days = (now - post_dt).total_seconds() / 86400
        norm_recency = math.exp(-0.693 * age_days / 30)  # half-life = 30 days
    except Exception:
        pass

    return (w_relevance * norm_relevance) + (w_likes * norm_likes) + (w_recency * norm_recency)


# ── Search Logic ──────────────────────────────────────────────────────────────

def search(query_str: str, sort_mode: str = "combined", top_n: int = 50):
    """
    Runs a PyLucene search across text, author, and linked_title fields.
    Returns top_n raw hits, then re-ranks based on sort_mode.
    """
    if not query_str.strip():
        return [], 0

    # Search across multiple fields simultaneously
    fields   = ["text", "author", "linked_title", "display_name"]
    boosts   = {"text": 2.0, "author": 1.0, "linked_title": 1.5, "display_name": 0.5}
    parser   = MultiFieldQueryParser(fields, _analyzer, boosts)
    parser.setDefaultOperator(QueryParser.Operator.OR)

    try:
        query = parser.parse(MultiFieldQueryParser.escape(query_str))
    except Exception:
        return [], 0

    # Get more than we need so we can re-rank
    top_docs = _searcher.search(query, top_n)
    hits     = top_docs.scoreDocs
    total    = top_docs.totalHits.value

    # Extract query terms for snippet generation
    query_terms = [t.strip() for t in query_str.split() if t.strip()]

    results = []
    for hit in hits:
        doc        = _searcher.doc(hit.doc)
        like_count = int(doc.get("like_count") or 0)
        created_at = doc.get("created_at") or ""
        text       = doc.get("text") or ""

        result = {
            "uri":          doc.get("uri") or "",
            "author":       doc.get("author") or "",
            "display_name": doc.get("display_name") or "",
            "text":         text,
            "created_at":   created_at,
            "like_count":   like_count,
            "repost_count": int(doc.get("repost_count") or 0),
            "reply_count":  int(doc.get("reply_count") or 0),
            "linked_url":   doc.get("linked_url") or "",
            "linked_title": doc.get("linked_title") or "",
            "lucene_score": round(hit.score, 4),
            "snippet":      generate_snippet(text, query_terms),
        }

        # Compute combined score for re-ranking
        result["combined_score"] = combined_score(
            hit.score, like_count, created_at
        )

        results.append(result)

    # Sort based on user's chosen mode
    if sort_mode == "relevance":
        results.sort(key=lambda r: r["lucene_score"], reverse=True)
    elif sort_mode == "likes":
        results.sort(key=lambda r: r["like_count"], reverse=True)
    elif sort_mode == "newest":
        results.sort(key=lambda r: r["created_at"], reverse=True)
    else:  # combined (default)
        results.sort(key=lambda r: r["combined_score"], reverse=True)

    return results[:RESULTS_PER_PAGE], int(total)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search_route():
    query_str = request.args.get("q", "").strip()
    sort_mode = request.args.get("sort", "combined")

    results, total = [], 0
    if query_str:
        results, total = search(query_str, sort_mode)

    return render_template(
        "results.html",
        query=query_str,
        results=results,
        total=total,
        sort_mode=sort_mode,
        count=len(results),
    )


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bluesky search web interface.")
    parser.add_argument("--index-dir", default="./index", help="Path to PyLucene index")
    parser.add_argument("--port",      type=int, default=5000)
    parser.add_argument("--host",      default="0.0.0.0")
    args = parser.parse_args()

    init_lucene(args.index_dir)
    app.run(host=args.host, port=args.port, debug=False)
