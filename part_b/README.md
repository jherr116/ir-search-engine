# IR Project — Part B: Search Engine

## Overview

Part B builds a search engine on top of the Bluesky data collected in Part A.

- **B1** — `indexer.py`: Parses JSONL files and builds a PyLucene index
- **B2** — `app.py`: Flask web interface that searches the index

**Extra credit implemented:**
- ✅ Custom snippet generation with query term highlighting
- ✅ Combined ranking: PyLucene relevance + like count + recency

---

## Folder Structure

```
part_b/
├── indexer.sh          ← Step 1: build the index (run this first)
├── indexer.py          ← PyLucene indexing logic
├── app.py              ← Flask search application
├── requirements.txt    ← Python dependencies
├── templates/
│   ├── index.html      ← Search home page
│   └── results.html    ← Search results page
└── index/              ← Created automatically by indexer.sh
```

---

## How to Run

### Prerequisites

- Python 3.9+
- PyLucene installed (see note below)
- Data collected from Part A in `../data/`

> ⚠️ **PyLucene Note**: PyLucene requires Java and is not a simple pip install.
> Follow the official guide: https://lucene.apache.org/pylucene/install.html
> Or install via conda: `conda install -c conda-forge pylucene`

### Step 1 — Build the Index

```bash
cd part_b
chmod +x indexer.sh
./indexer.sh ./index ../data
```

This reads all `.jsonl` files from `../data/` and writes a Lucene index to `./index/`.

### Step 2 — Start the Search UI

```bash
python3 app.py --index-dir ./index
```

Then open **http://localhost:5000** in your browser.

---

## Search Features

### Fields Indexed

| Field | Searchable | Stored | Notes |
|---|---|---|---|
| `text` | ✅ (boost 2×) | ✅ | Main post body |
| `author` | ✅ (boost 1×) | ✅ | Bluesky handle |
| `display_name` | ✅ | ✅ | Display name |
| `linked_title` | ✅ (boost 1.5×) | ✅ | Embedded page title |
| `uri` | — | ✅ | Unique post ID |
| `created_at` | — | ✅ | ISO 8601 timestamp |
| `like_count` | range query | ✅ | For ranking |
| `repost_count` | range query | ✅ | For ranking |

### Sort Modes

| Mode | Description |
|---|---|
| **Combined** *(default)* | 60% relevance + 25% likes + 15% recency |
| **Relevance** | Pure PyLucene BM25 score |
| **Most Liked** | Sorted by like count descending |
| **Newest** | Sorted by creation date descending |

### Combined Ranking Formula

```
final = 0.60 × norm_relevance + 0.25 × log_norm_likes + 0.15 × recency_decay

where:
  norm_relevance = min(lucene_score / 20, 1.0)
  log_norm_likes = log(1 + likes) / log(1 + max_likes)
  recency_decay  = exp(-0.693 × age_days / 30)   # 30-day half-life
```

### Snippet Generation (Extra Credit)

- Splits post text into sentences
- Scores each sentence by how many query terms it contains
- Returns the best sentence, truncated to 200 characters
- Wraps matched terms in `<mark>` tags for highlighting
- Does **not** use PyLucene's built-in highlighter

---

## Architecture

```
data/*.jsonl
     │
     ▼
 indexer.py
 ├── StandardAnalyzer (tokenization, stop words, stemming)
 ├── TextField (text, author, linked_title) — searchable + stored
 ├── StoredField (uri, created_at) — stored only
 └── LongPoint + NumericDocValuesField (like_count) — numeric/sortable
     │
     ▼
 index/   (Lucene FSDirectory on disk)
     │
     ▼
 app.py (Flask)
 ├── MultiFieldQueryParser — searches text + author + linked_title simultaneously
 ├── generate_snippet()    — custom sentence-level snippet with highlighting
 ├── combined_score()      — re-ranks top-50 Lucene hits by combined signal
 └── /search route         — returns top 10 results as HTML
     │
     ▼
 Browser (http://localhost:5000)
```

---

## Limitations

- PyLucene scores are used to retrieve top-50 candidates before re-ranking; results beyond rank 50 are not considered for combined scoring.
- Recency scoring assumes posts are recent; very old posts will rank lower regardless of relevance.
- The index must be rebuilt if new data is collected (no incremental indexing).
