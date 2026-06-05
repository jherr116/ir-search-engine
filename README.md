# IR Search Engine — Bluesky Politics Search

**Course:** CS172 Information Retrieval · UC Riverside
**Dataset:** Bluesky posts about politics and elections
**Due:** June 5, 2026

---

## Project Overview

This project builds a full search engine over Bluesky social media posts focused on politics, in order to make searching simpler and easier for those who struggle navigating digital news.

- **Part A** — Collects posts from the Bluesky API and stores them as JSONL files
- **Part B** — Indexes the JSONL files with PyLucene and provides a Flask-based search UI

**Extra credit implemented:**
- ✅ Custom snippet generation with query term highlighting (no PyLucene highlighter used)
- ✅ Combined ranking: PyLucene relevance + like count + recency decay

---

## Architecture

```
Bluesky Search API
       │
       ▼
  part_a/collector.py
  (paginates API, deduplicates by URI, retries on failure)
       │
       ├── get_page_title() — fetches title of embedded URLs
       │
       ▼
  data/*.jsonl
  (one post per line, rotated at ~10 MB)
       │
       ▼
  part_b/indexer.py (PyLucene)
  ├── StandardAnalyzer — tokenization, stop words, lowercasing
  ├── TextField (text, author, linked_title) — searchable + stored
  ├── StoredField (uri, created_at) — stored only
  └── LongPoint + NumericDocValuesField (like_count) — numeric/sortable
       │
       ▼
  part_b/index/  (Lucene FSDirectory on disk)
       │
       ▼
  part_b/app.py (Flask)
  ├── MultiFieldQueryParser — searches text (2×) + linked_title (1.5×) + author (1×)
  ├── generate_snippet()   — custom sentence-level snippet with query highlighting
  ├── combined_score()     — re-ranks top-50 Lucene hits by combined signal
  └── /search route        — returns top 10 results as HTML
       │
       ▼
  Browser (http://localhost:5000)
```

---

## Folder Structure

```
ir-search-engine/
├── .devcontainer/
│   └── devcontainer.json    ← Docker PyLucene environment (one-click setup)
├── .gitignore
├── README.md
├── run.sh                   ← one-command launcher: builds index + starts UI
├── part_a/
│   ├── collector.sh         ← Part A entry point
│   ├── collector.py         ← Bluesky API collection logic
│   ├── verify_data.py       ← sanity check on collected data
│   └── requirements.txt
├── part_b/
│   ├── indexer.sh           ← Part B entry point
│   ├── indexer.py           ← PyLucene indexer
│   ├── app.py               ← Flask search UI
│   ├── requirements.txt
│   └── templates/
│       ├── index.html       ← search home page
│       └── results.html     ← search results page
└── data/                    ← gitignored, created by Part A
    ├── posts_001.jsonl
    ├── posts_002.jsonl
    └── ...
```

---

## Quick Start — Docker (Recommended, No Setup Required)

PyLucene is pre-built inside the container — no Java installation or compilation needed.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [VS Code](https://code.visualstudio.com)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Steps

**1. Clone and open the repo**
```bash
git clone https://github.com/yourusername/ir-search-engine.git
cd ir-search-engine
```

**2. Reopen in Container**
```
Cmd+Shift+P → Dev Containers: Reopen in Container
```
Wait ~2 minutes for the container to build. Only slow the first time.

**3. Collect data (Part A)**
```bash
cd part_a
./collector.sh "politics" 5000 ../data
```

**4. Build index and launch search UI (Part B)**
```bash
cd ..
./run.sh
```

**5. Open in browser**
```
http://localhost:5000
```

---

## Alternative — UCR Bolt Server

If you have UCR access, PyLucene is pre-installed on the class server.
Requires UCR Cisco AnyConnect VPN if off campus.

```bash
# 1. SSH into bolt
ssh netid@bolt.cs.ucr.edu

# 2. Activate the PyLucene environment
cs172_login

# 3. Clone the repo
git clone https://github.com/yourusername/ir-search-engine.git
cd ir-search-engine

# 4. Collect data
cd part_a
./collector.sh "politics" 5000 ../data

# 5. Build index and launch
cd ..
./run.sh

# 6. Open in browser (VPN required)
http://class-042.cs.ucr.edu:8888
```

---

## Part A — Data Collection

### Data Format

Each line in a `.jsonl` file is one JSON post with these fields:

| Field | Description | Used in Part B |
|---|---|---|
| `uri` | Unique post identifier | Document ID |
| `author_handle` | Bluesky username | Searchable field |
| `author_display_name` | Display name | Searchable field |
| `text` | Post body | **Primary search field** |
| `created_at` | ISO 8601 timestamp | Time-based ranking |
| `like_count` | Number of likes | Popularity ranking |
| `repost_count` | Number of reposts | Popularity ranking |
| `reply_count` | Number of replies | Popularity ranking |
| `langs` | Language tags | Filtering |
| `linked_url` | Embedded URL (if any) | — |
| `linked_page_title` | Title of linked page | Searchable field |

### Running the Collector Manually

```bash
cd part_a
chmod +x collector.sh
./collector.sh "<query>" <max-posts> <output-dir>

# Example:
./collector.sh "politics" 5000 ../data
```

### Verifying the Data

```bash
python3 verify_data.py --data-dir ../data
```

Prints a summary of files, post count, total size, and a sample post.

### Part A Limitations

- The Bluesky Search API only returns recent posts — no full historical access
- URL title fetching may fail for pages behind paywalls or bot protection
- Rate limited to ~3,000 requests per 5 minutes when authenticated
- Deduplication (`seen_uris` set) resets if the collector is restarted mid-run

---

## Part B — Search Engine

### B1: Index Structure

Built with PyLucene using the following field types:

| Field | Type | Tokenized | Stored | Search Boost | Purpose |
|---|---|---|---|---|---|
| `text` | TextField | ✅ | ✅ | 2.0× | Main post body |
| `linked_title` | TextField | ✅ | ✅ | 1.5× | Embedded URL page title |
| `author` | TextField | ✅ | ✅ | 1.0× | Bluesky handle |
| `display_name` | TextField | ✅ | ✅ | 0.5× | Display name |
| `uri` | StoredField | ❌ | ✅ | — | Unique post ID |
| `created_at` | StoredField | ❌ | ✅ | — | Timestamp for recency |
| `like_count` | LongPoint + NumericDocValuesField | ❌ | ✅ | — | Numeric ranking |
| `repost_count` | StoredField | ❌ | ✅ | — | Stored for display |

**Analyzer:** StandardAnalyzer — handles tokenization, lowercasing, and stop word removal. Sufficient for social media text without needing custom stemming rules.

**Storage:** FSDirectory — stores the index on disk at `./index/` so it persists between app restarts without rebuilding.

### B2: Search Algorithm

**Layer 1 — Retrieval:**
MultiFieldQueryParser fetches the top 50 candidate posts from the Lucene index simultaneously across all fields using BM25 scoring.

**Layer 2 — Re-ranking (Extra Credit):**

```
final_score = 0.60 × norm_relevance + 0.25 × log_norm_likes + 0.15 × recency_decay

where:
  norm_relevance  = min(lucene_score / 20, 1.0)
  log_norm_likes  = log(1 + likes) / log(1 + max_likes)
  recency_decay   = exp(-0.693 × age_days / 30)   ← 30-day half-life
```

Top 10 results are returned to the user ordered by final score.

### Sort Modes

| Mode | Description |
|---|---|
| **Combined** *(default)* | 60% relevance + 25% likes + 15% recency |
| **Relevance** | Pure PyLucene BM25 score |
| **Most Liked** | Sorted by like_count descending |
| **Newest** | Sorted by created_at descending |

### Snippet Generation (Extra Credit)

Custom algorithm — PyLucene's built-in highlighter is **NOT** used:

1. Split post text into sentences
2. Score each sentence by number of query terms matched
3. Return the highest scoring sentence, truncated to 200 characters
4. Wrap matched terms in `<mark>` tags for yellow highlighting in the UI

### Running Part B Manually

```bash
# Step 1 — Build the index
cd part_b
chmod +x indexer.sh
./indexer.sh ./index ../data

# Step 2 — Start the search UI
python3 app.py --index-dir ./index --port 5000

# Step 3 — Open in browser
http://localhost:5000
```

### Part B Limitations

- Search covers only the collected dataset, not all of Bluesky
- Index must be fully rebuilt if new data is collected — no incremental indexing
- Re-ranking only considers top 50 Lucene candidates; results beyond rank 50 are not re-ranked
- Very short posts (one sentence) don't benefit much from snippet scoring
- Recency scoring penalizes older posts regardless of relevance

---

## Collaboration Details

### Part A

| Member | Contribution |
|---|---|
| Javier Herrera Jr | Created code skeleton, created Bluesky account, edited shell script for login, created GitHub repo, debugger |
| [Name 2] | [contribution] |
| [Name 3] | [contribution] |
| [Name 4] | [contribution] |
| [Name 5] | [contribution] |

### Part B

| Member | Contribution |
|---|---|
| Javier Herrera Jr | Created Flask UI and skeleton, implemented PyLucene indexer, implemented extra credit (snippets + combined ranking), laid out report, assigned team parts |
| [Name 2] | [contribution] |
| [Name 3] | [contribution] |
| [Name 4] | [contribution] |
| [Name 5] | [contribution] |
