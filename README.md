# IR Project — Bluesky Search Engine

**Team Members:** [List names and contributions here]
**Course:** Information Retrieval
**Part A:** Bluesky Data Collector

---

## Project Overview

This project builds a search engine over Bluesky social media posts.

- **Part A** (this folder): Collects posts from the Bluesky API and stores them as JSONL files.
- **Part B** (separate): Indexes the JSONL files with PyLucene and provides a Flask-based search UI.

---

## Folder Structure

```
bluesky_ir_project/
├── README.md               ← You are here
│
├── part_a/                 ← Data collection (Part A)
│   ├── collector.sh        ← Entry point (run this to collect data)
│   ├── collector.py        ← Main collection logic
│   ├── verify_data.py      ← Sanity check after collection
│   └── requirements.txt    ← Python dependencies
│
├── part_b/                 ← Search engine (Part B — coming later)
│   └── (indexer and Flask app go here)
│
└── data/                   ← Output JSONL files (created automatically)
    ├── posts_001.jsonl
    ├── posts_002.jsonl
    └── ...
```

---

## Part A — How to Run

### Step 1: Prerequisites

- Python 3.9 or higher
- pip

Check with:
```bash
python3 --version
pip --version
```

### Step 2: Get a Bluesky Account & App Password

1. Create a free account at [bsky.app](https://bsky.app)
2. Go to **Settings → Privacy and Security → App Passwords**
3. Click **Add App Password**, name it `ir-project`, copy the password

> ⚠️ Use an **App Password**, NOT your main account password.

### Step 3: Set Credentials

**Option A — Environment variables (recommended):**
```bash
export BSKY_HANDLE="yourhandle.bsky.social"
export BSKY_PASSWORD="xxxx-xxxx-xxxx-xxxx"
```

**Option B — Edit collector.sh directly:**
Open `part_a/collector.sh` and fill in the CONFIGURATION section at the top.

### Step 4: Run the Collector

```bash
cd part_a
chmod +x collector.sh

./collector.sh "<query>" <max-posts> <output-dir>
```

**Example:**
```bash
./collector.sh "artificial intelligence" 5000 ../data
```

| Argument | Description | Example |
|---|---|---|
| `<query>` | Topic to search for | `"climate change"` |
| `<max-posts>` | How many posts to collect | `5000` |
| `<output-dir>` | Where to save JSONL files | `../data` |

The script will:
1. Install Python dependencies automatically
2. Connect to the Bluesky API
3. Collect and save posts as `posts_001.jsonl`, `posts_002.jsonl`, etc.
4. Each file is rotated at ~10 MB (as required by the spec)

### Step 5: Verify the Data

```bash
python3 verify_data.py --data-dir ../data
```

This will print a summary of how many posts were collected, total size,
and a sample post so you can confirm the fields look correct.

---

## Data Format

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

---

## Architecture

```
Bluesky Search API
       │
       ▼
  collector.py
  (paginates API, deduplicates by URI)
       │
       ├── get_page_title()  ← fetches title of embedded URLs
       │
       ▼
  RotatingJSONLWriter
  (rotates files at 10 MB)
       │
       ▼
  data/posts_001.jsonl
  data/posts_002.jsonl
  ...
       │
       ▼  (Part B)
  PyLucene Indexer → Flask Search UI
```

---

## Limitations

- The Bluesky Search API does not guarantee full coverage of all historical posts; it searches recent content.
- URL title fetching may fail for pages behind paywalls or with bot protection.
- Rate limits apply to the REST API (~3,000 requests per 5 minutes when authenticated).

---

## Collaboration Details

| Member | Contribution |
|---|---|
| [Name 1] | [e.g., Collector script, API integration] |
| [Name 2] | [e.g., URL enrichment, file rotation] |
| [Name 3] | [e.g., Verification script, README] |
| [Name 4] | [e.g., Part B indexer] |
| [Name 5] | [e.g., Part B Flask UI] |
