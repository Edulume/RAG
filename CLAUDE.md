# Edulume RAG

Production RAG system for multi-board (CBSE, ICSE, etc.) content search and question bank queries.

## What This Is

Central RAG (Retrieval-Augmented Generation) database that powers:
- **Chapter Generator** - AI-generated adaptive learning content
- **Question Assignment** - Level-aware question selection
- **Intelligence Engine** - Gap analysis & recommendations

## Current Status

**Live at `http://13.232.174.33`** - CBSE Class 10 indexed, add more classes/boards as needed.

| Data | Status | Count |
|------|--------|-------|
| CBSE Class 10 | ✅ Indexed | 4,680 chunks |
| Questions (Exemplar) | ✅ Loaded | 2,159 |
| CBSE Class 6-9 | ❌ Pending | Add from pendrive |
| CBSE Class 11-12 | ❌ Pending | Add from pendrive |
| ICSE | ❌ Pending | Add when available |

## Production

**URL:** `http://13.232.174.33`

| Resource | Details |
|----------|---------|
| Server | AWS EC2 t3.small (ap-south-1) |
| IP | 13.232.174.33 |
| Cost | ~$17/month |

### Test Production
```bash
# List available boards
curl http://13.232.174.33/boards

# Board-specific health
curl http://13.232.174.33/cbse/health

# Board-specific search
curl -X POST http://13.232.174.33/cbse/search \
  -H "Content-Type: application/json" \
  -d '{"query": "photosynthesis", "limit": 3}'

# Board-specific questions
curl -X POST http://13.232.174.33/cbse/questions \
  -H "Content-Type: application/json" \
  -d '{"filters": {"class": 10, "subject": "Mathematics"}, "limit": 5}'

# Board-specific stats
curl http://13.232.174.33/cbse/stats

# Legacy endpoints (default to CBSE)
curl http://13.232.174.33/health
curl http://13.232.174.33/stats
```

### Update Production
```bash
# SSH to server
ssh -i ~/edulume-rag-key.pem ubuntu@13.232.174.33

# Pull latest & restart
cd /home/ubuntu/RAG && git pull
sudo systemctl restart rag

# Check logs
sudo journalctl -u rag -f
```

### Re-deploy Data
```bash
# From local Mac - copy board index
scp -i ~/edulume-rag-key.pem -r indexes/cbse/* \
  ubuntu@13.232.174.33:/home/ubuntu/RAG/indexes/cbse/

# Copy question bank
scp -i ~/edulume-rag-key.pem data/question-bank.csv \
  ubuntu@13.232.174.33:/home/ubuntu/RAG/data/

# Restart service
ssh -i ~/edulume-rag-key.pem ubuntu@13.232.174.33 "sudo systemctl restart rag"
```

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
# List available boards
curl http://localhost:6969/boards

# Board-specific endpoints
curl http://localhost:6969/cbse/health
curl http://localhost:6969/cbse/stats

curl -X POST http://localhost:6969/cbse/search \
  -H "Content-Type: application/json" \
  -d '{"query": "photosynthesis", "limit": 3}'

curl -X POST http://localhost:6969/cbse/questions \
  -H "Content-Type: application/json" \
  -d '{"filters": {"class": 10, "subject": "Mathematics"}, "limit": 5}'

# Legacy endpoints (backward compatible, default to CBSE)
curl http://localhost:6969/health
curl http://localhost:6969/stats
```

## API Endpoints

### Board-Specific Endpoints (v2.0)

| Endpoint | Description |
|----------|-------------|
| `GET /boards` | List available boards |
| `GET /{board}/health` | Board health check |
| `GET /{board}/stats` | Board statistics |
| `POST /{board}/search` | Search board content |
| `POST /{board}/questions` | Query board questions |

### POST /{board}/search
Search textbook content for specific board.

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

**Response:** Returns matching content chunks with metadata (board, class, subject, chapter).

### POST /{board}/questions
Query question bank for specific board.

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

**Response:** Returns questions with answers, solutions, and full metadata including board.

### Legacy Endpoints (backward compatible)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check (defaults to CBSE) |
| `GET /stats` | Statistics (defaults to CBSE) |
| `POST /search` | Search (defaults to CBSE) |
| `POST /questions` | Questions (defaults to CBSE) |

## Directory Structure

```
RAG/
├── api/
│   └── server.py              # FastAPI server (port 6969)
├── pipelines/
│   ├── index-ncert/
│   │   └── index.py           # Book indexing with --board flag
│   └── extract-questions/     # Question extraction (Claude Vision)
├── data/                      # Gitignored
│   ├── CBSE/
│   │   └── Class-10/          # 154 PDFs (390MB)
│   ├── ICSE/                  # Add when available
│   │   └── ...
│   └── question-bank.csv      # 2,159 questions (with board column)
├── indexes/                   # Gitignored
│   ├── cbse/
│   │   ├── index.faiss        # CBSE vector index
│   │   └── documents.pkl      # CBSE document metadata
│   └── icse/                  # Add when indexed
│       └── ...
├── logs/
│   └── extraction-log.csv     # Question extraction progress
└── .venv/                     # Python virtual environment
```

## Commands

### Index Books by Board
```bash
source .venv/bin/activate

# Index CBSE (default)
python pipelines/index-ncert/index.py --board cbse

# Index specific board with custom source
python pipelines/index-ncert/index.py --board icse --source data/ICSE

# Clear and rebuild board index
python pipelines/index-ncert/index.py --board cbse --clear

# Search test
python pipelines/index-ncert/index.py --board cbse --search "photosynthesis"

# Show board stats
python pipelines/index-ncert/index.py --board cbse --stats
```

### Add More Classes
```bash
# Copy from pendrive to board folder
cp -r /Volumes/PENDRIVE/Class-9/* data/CBSE/Class-9/
cp -r /Volumes/PENDRIVE/Class-11/* data/CBSE/Class-11/

# Re-index board
python pipelines/index-ncert/index.py --board cbse

# Restart server
pkill -f "python api/server.py"
nohup python api/server.py > /tmp/rag-server.log 2>&1 &
```

### Add New Board
```bash
# Create board data directory
mkdir -p data/ICSE/Class-10

# Copy books
cp -r /Volumes/PENDRIVE/ICSE/Class-10/* data/ICSE/Class-10/

# Index the board
python pipelines/index-ncert/index.py --board icse

# Add board column to questions (if needed)
# Questions already have 'board' column - just add questions with board=icse
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
| `api/server.py` | FastAPI server with multi-board endpoints |
| `pipelines/index-ncert/index.py` | Book indexing with --board flag |
| `pipelines/extract-questions/` | Claude Vision extraction pipeline |
| `data/question-bank.csv` | Extracted questions with board column |

## Data Sources

### Books (for /{board}/search)
- CBSE Class 6-12 textbooks
- Currently: CBSE Class 10 indexed (154 PDFs → 4,680 chunks)
- Subjects: Math, Science, SST, English, Hindi, Sanskrit, PE

### Question Bank (for /{board}/questions)
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

1. **Add more CBSE classes** - Copy Class 6-9, 11-12 from pendrive, re-index with `--board cbse`
2. **Add ICSE board** - When available, create `data/ICSE/` and index with `--board icse`
3. **Complete question extraction** - Run extraction on remaining 675 PDFs

---

*Last Updated: March 2026*
