# Edulume RAG

> Production RAG Database for Edulume's Adaptive Learning Platform

---

## What is This?

Edulume's central **Retrieval-Augmented Generation (RAG)** system that powers:
- **Chapter Generator** - AI-generated learning content
- **Question Assignment** - Adaptive question selection
- **Intelligence Engine** - Gap analysis & recommendations

---

## Data Sources

### 1. NCERT Content RAG
Full textbook content for Classes 6-12.

| Class | Subjects | Status |
|-------|----------|--------|
| Class 6 | Math, Science, SST, English, Hindi | Pending |
| Class 7 | Math, Science, SST, English, Hindi | Pending |
| Class 8 | Math, Science, SST, English, Hindi | Pending |
| Class 9 | Math, Science, SST, English, Hindi | Pending |
| Class 10 | Math, Science, SST, English, Hindi | Pending |
| Class 11 | Physics, Chemistry, Math, Biology, English | Pending |
| Class 12 | Physics, Chemistry, Math, Biology, English | Pending |

**Use Case:** Search NCERT content to generate adaptive chapters for any class level.

### 2. Question Bank RAG
841 PDFs with 25,000+ questions (extraction in progress).

| Source | PDFs | Questions | Status |
|--------|------|-----------|--------|
| NCERT Exemplar | 166 | ~8,000 | Extracting |
| CBSE Class 10 PYQs | 146 | ~5,000 | Pending |
| CBSE Class 12 PYQs | 420 | ~15,000 | Pending |
| JEE Main PYQs | 66 | ~3,000 | Pending |
| JEE Advanced PYQs | 28 | ~1,500 | Pending |
| NEET PYQs | 15 | ~800 | Pending |

**Use Case:** Auto-assign questions based on student's V×H level (9×8 difficulty matrix).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CONSUMERS                              │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│     LMS     │ Intelligence│   Chapter   │   Assignment    │
│  Frontend   │     API     │  Generator  │    Engine       │
└──────┬──────┴──────┬──────┴──────┬──────┴────────┬────────┘
       │             │             │               │
       └─────────────┴──────┬──────┴───────────────┘
                            │
                            ▼
              ┌──────────────────────────┐
              │        RAG API           │
              │   rag.edulume.com        │
              ├──────────────────────────┤
              │ POST /search             │
              │ POST /questions          │
              │ GET  /chapters/{topic}   │
              └────────────┬─────────────┘
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
   ┌─────────────────┐          ┌─────────────────┐
   │  NCERT Content  │          │  Question Bank  │
   │   FAISS Index   │          │   FAISS Index   │
   └─────────────────┘          └─────────────────┘
```

---

## Directory Structure

```
edulume-rag/
├── data/                   # Raw data (gitignored)
│   ├── ncert-books/        # NCERT PDFs Class 6-12
│   ├── question-bank/      # Question PDFs (841 files)
│   └── question-bank.csv   # Extracted questions
│
├── indexes/                # FAISS vector indexes
│   ├── ncert-content/      # Textbook content index
│   └── questions/          # Question bank index
│
├── pipelines/              # Data processing
│   ├── extract-questions/  # Question extraction (Claude Vision)
│   ├── index-ncert/        # NCERT book indexing
│   └── shared/             # Common utilities
│
├── api/                    # FastAPI server
│   ├── routes/             # API endpoints
│   └── services/           # RAG services
│
└── agents/                 # Future: Auto-indexing
    ├── watcher.py          # Watch for new PDFs
    └── indexer.py          # Background indexing
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Bun (for TypeScript pipelines)
- Poppler (for PDF processing)

### Setup
```bash
# Clone
git clone https://github.com/Edulume/RAG.git
cd RAG

# Install Python deps
pip install -r requirements.txt

# Install Bun deps (for extraction pipeline)
cd pipelines/extract-questions && bun install

# Copy env
cp .env.example .env
# Add your ANTHROPIC_API_KEY, OPENAI_API_KEY
```

### Run API Server
```bash
python -m api.main
# Server at http://localhost:6969
```

### Run Question Extraction
```bash
cd pipelines/extract-questions
bun run src/main.ts
```

---

## API Endpoints

### Search NCERT Content
```http
POST /search
Content-Type: application/json

{
  "query": "Photosynthesis",
  "filters": {
    "class": 10,
    "subject": "Biology"
  },
  "limit": 5
}
```

### Get Questions
```http
POST /questions
Content-Type: application/json

{
  "filters": {
    "class": 10,
    "subject": "Mathematics",
    "topic": "Quadratic Equations",
    "verticalLevel": [2, 3, 4],
    "horizontalLevel": [1, 2],
    "questionType": ["MCQ", "Short"]
  },
  "limit": 10
}
```

---

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

---

## Extraction Pipeline

Uses **Claude Vision API** (Haiku model) for question extraction.

| Metric | Value |
|--------|-------|
| Model | claude-3-5-haiku-20241022 |
| Cost | ~$0.005/question |
| Validation Rate | 98.1% |
| Fields Extracted | 16 required + 20 optional |

---

## Related Repos

| Repo | Purpose |
|------|---------|
| [edulume/intelligence](https://github.com/edulume/intelligence) | Student Intelligence Engine |
| [edulume/lms](https://github.com/edulume/lms) | Learning Management System |

---

## License

Proprietary - Edulume Education Pvt. Ltd.

---

*Last Updated: March 2026*
