# Edulume RAG

Production RAG system for NCERT content search and question bank queries.

## What This Is

Central RAG (Retrieval-Augmented Generation) database that powers:
- **Chapter Generator** - AI-generated adaptive learning content
- **Question Assignment** - Level-aware question selection
- **Intelligence Engine** - Gap analysis & recommendations

## Current Status

**Class 10 indexed and working.** Add more classes from pendrive as needed.

| Data | Status | Count |
|------|--------|-------|
| NCERT Class 10 | ✅ Indexed | 4,680 chunks |
| Questions (Exemplar) | ✅ Loaded | 2,159 |
| NCERT Class 6-9 | ❌ Pending | Add from pendrive |
| NCERT Class 11-12 | ❌ Pending | Add from pendrive |

## Quick Start

### Start API Server
```bash
cd /Users/rahulsain/Documents/kzr/Edulume/RAG
source .venv/bin/activate
python api/server.py

# Or in background:
nohup python api/server.py > /tmp/rag-server.log 2>&1 &
```

Server runs at: `http://localhost:6969`

### Test Endpoints
```bash
# Health check
curl http://localhost:6969/health

# Search NCERT content
curl -X POST http://localhost:6969/search \
  -H "Content-Type: application/json" \
  -d '{"query": "photosynthesis", "limit": 3}'

# Query questions
curl -X POST http://localhost:6969/questions \
  -H "Content-Type: application/json" \
  -d '{"filters": {"class": 10, "subject": "Mathematics"}, "limit": 5}'

# Get stats
curl http://localhost:6969/stats
```

## API Endpoints

### POST /search
Search NCERT textbook content.

```json
{
  "query": "quadratic equations solving methods",
  "filters": {
    "class": 10,
    "subject": "Mathematics"
  },
  "limit": 5
}
```

**Response:** Returns matching content chunks with metadata (class, subject, chapter).

### POST /questions
Query question bank with filters.

```json
{
  "filters": {
    "class": 10,
    "subject": "Mathematics",
    "topic": "Polynomials",
    "vertical_level": [2, 3, 4],
    "horizontal_level": [1, 2],
    "question_type": ["MCQ", "Short"]
  },
  "limit": 10,
  "offset": 0
}
```

**Response:** Returns questions with answers, solutions, and full metadata.

### GET /stats
Returns index statistics (document counts, subjects, etc.).

### GET /health
Health check endpoint.

## Directory Structure

```
RAG/
├── api/
│   └── server.py              # FastAPI server (port 6969)
├── pipelines/
│   ├── index-ncert/
│   │   └── index.py           # NCERT book indexing
│   └── extract-questions/     # Question extraction (Claude Vision)
├── data/                      # Gitignored
│   ├── ncert-books/
│   │   └── Class-10/          # 154 PDFs (390MB)
│   └── question-bank.csv      # 2,159 questions
├── indexes/                   # Gitignored
│   └── ncert-content/
│       ├── index.faiss        # Vector index
│       └── documents.pkl      # Document metadata
├── logs/
│   └── extraction-log.csv     # Question extraction progress
└── .venv/                     # Python virtual environment
```

## Commands

### Index NCERT Books
```bash
source .venv/bin/activate

# Index specific class
python pipelines/index-ncert/index.py --source data/ncert-books/Class-10

# Index all classes
python pipelines/index-ncert/index.py

# Clear and rebuild
python pipelines/index-ncert/index.py --clear

# Search test
python pipelines/index-ncert/index.py --search "photosynthesis"

# Show stats
python pipelines/index-ncert/index.py --stats
```

### Add More Classes
```bash
# Copy from pendrive
cp -r /Volumes/PENDRIVE/Class-9/* data/ncert-books/Class-9/
cp -r /Volumes/PENDRIVE/Class-11/* data/ncert-books/Class-11/

# Re-index
python pipelines/index-ncert/index.py

# Restart server
pkill -f "python api/server.py"
nohup python api/server.py > /tmp/rag-server.log 2>&1 &
```

### Extract Questions (from PDFs)
```bash
cd pipelines/extract-questions
bun install
cp .env.example .env  # Add ANTHROPIC_API_KEY
bun run src/main.ts
```

## V×H Leveling System

### Vertical Levels (0-8) - Student Mastery
| Level | Name | Description |
|-------|------|-------------|
| 0 | Beginner | Basic recognition |
| 1-2 | Foundation | Understanding fundamentals |
| 3-4 | Intermediate | Multi-step problems |
| 5-6 | Advanced | Analytical reasoning |
| 7 | Competitive | JEE/NEET level |
| 8 | Master | Olympiad level |

### Horizontal Levels (1-8) - Source Difficulty
| Level | Sources |
|-------|---------|
| 1-2 | NCERT Textbook |
| 3-4 | NCERT Exemplar |
| 5-6 | Reference Books |
| 7-8 | PYQs, Competitive |

## Tech Stack

- **Vector Store:** FAISS (Facebook AI Similarity Search)
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **API:** FastAPI + Uvicorn
- **Extraction:** Claude Vision API (Haiku)
- **Runtime:** Python 3.14

## Environment Setup

```bash
# Create venv (if not exists)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Key Files

| File | Purpose |
|------|---------|
| `api/server.py` | FastAPI server with /search and /questions |
| `pipelines/index-ncert/index.py` | NCERT book indexing to FAISS |
| `pipelines/extract-questions/` | Claude Vision extraction pipeline |
| `data/question-bank.csv` | Extracted questions with metadata |

## Data Sources

### NCERT Books (for /search)
- Class 6-12 textbooks
- Currently: Class 10 indexed (154 PDFs → 4,680 chunks)
- Subjects: Math, Science, SST, English, Hindi, Sanskrit, PE

### Question Bank (for /questions)
| Source | PDFs | Status |
|--------|------|--------|
| NCERT Exemplar | 166 | Extracting |
| CBSE Class 10 PYQs | 146 | Pending |
| CBSE Class 12 PYQs | 420 | Pending |
| JEE Main PYQs | 66 | Pending |
| JEE Advanced PYQs | 28 | Pending |
| NEET PYQs | 15 | Pending |

## Related Repos

| Repo | Purpose |
|------|---------|
| [edulume/intelligence](https://github.com/edulume/intelligence) | Student Intelligence Engine |

## Git

- Commit messages: short, lowercase
- Never add `Co-Authored-By` to commits
- Data files (`data/`, `indexes/`) are gitignored

## Next Steps

1. **Add more classes** - Copy Class 6-9, 11-12 from pendrive
2. **Complete question extraction** - Run extraction on remaining 675 PDFs
3. **Deploy** - Set up `rag.edulume.com` for production

---

*Last Updated: March 2026*
