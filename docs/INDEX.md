# RAG System - Question Bank & NCERT Content

Complete reference for Edulume's dual RAG architecture.

---

## 📁 Directory Structure

```
rag/
├── data/
│   ├── question-bank/          # 841 PDFs (2.5 GB) organized by source
│   │   ├── NCERT-Exemplar/     # 166 PDFs (202 MB)
│   │   ├── CBSE-PYQ/           # 566 PDFs (1.9 GB)
│   │   ├── JEE-PYQ/            # 94 PDFs (226 MB)
│   │   ├── NEET-PYQ/           # 15 PDFs (29 MB)
│   │   └── Reference-Books/    # Oswaal samples
│   └── documents/              # NCERT textbooks (59 books)
│
├── scripts/
│   └── downloads/              # Automated collection scripts
│
├── question-bank-template.csv  # Excel template for manual tagging
│
└── Documentation (below)
```

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| **COLLECTION-GUIDE.md** | Full collection status (841 PDFs breakdown) |
| **MANUAL-EXTRACTION-PLAN.md** | Phase 1 manual extraction workflow (100 questions) |
| **QUESTION-BANK-TEMPLATE.md** | Complete 36-field metadata schema documentation |
| **NEXT-STEPS-QUESTION-EXTRACTION.md** | Full implementation roadmap (3 phases, 4 months) |
| **AUTOMATION-GUIDE.md** | Automation scripts guide |

---

## 🎯 Current Status

### Collection: ✅ Complete
**841 PDFs (2.5 GB) collected**

| Source | PDFs | Size | Location |
|--------|------|------|----------|
| NCERT Exemplar | 166 | 202 MB | `data/question-bank/NCERT-Exemplar/` |
| CBSE Class 10 PYQs | 146 | 606 MB | `data/question-bank/CBSE-PYQ/Class-10/` |
| CBSE Class 12 PYQs | 420 | 1.3 GB | `data/question-bank/CBSE-PYQ/Class-12/` |
| JEE Main PYQs | 66 | 87 MB | `data/question-bank/JEE-PYQ/JEE-Main/` |
| JEE Advanced PYQs | 28 | 139 MB | `data/question-bank/JEE-PYQ/JEE-Advanced/` |
| NEET PYQs | 15 | 29 MB | `data/question-bank/NEET-PYQ/` |

### Extraction: 🚧 In Progress
**Phase 1: Manual extraction of 100 gold-standard questions**

Current task: Extract first 10 questions from NCERT Exemplar Class 10 Math

---

## 🚀 Quick Start

### Manual Extraction (Current Task)

1. **Open template**: `question-bank-template.csv`
2. **Open first PDF**: `data/question-bank/NCERT-Exemplar/Class-10/Mathematics/Chapter-02.pdf`
3. **Follow workflow**: See `MANUAL-EXTRACTION-PLAN.md`
4. **Extract 10 questions** (Session 1: 2 hours)

### Running Download Scripts

```bash
# All scripts in scripts/downloads/
bun run scripts/downloads/download-jee-advanced.ts
bun run scripts/downloads/download-neet-neetprep.ts
```

---

## 📊 System Architecture

### Dual RAG Design

1. **Question Bank RAG** (this repository)
   - 841 PDFs with rich metadata
   - Auto-assignment based on student level
   - Background assessments 2x/month

2. **NCERT Content RAG**
   - 59 NCERT textbooks
   - NotebookLM integration for content generation
   - 10-part universal chapter structure

### Student Leveling

- **9 vertical levels** (0-8: Beginner → Master)
- **4 horizontal sub-levels** per vertical (Easy, Medium, Hard, Bridge)
- **Total: 36 difficulty buckets** for granular matching

### Question Metadata

- **16 required fields** (question_id, source, levels, solution, etc.)
- **20 optional fields** (image paths, video links, etc.)
- **Question ID format**: `Q_{SOURCE}_{CLASS}_{SUBJECT}_{CHAPTER}_{NUMBER}`

Full schema: See `QUESTION-BANK-TEMPLATE.md`

---

## 📝 Next Steps

### Immediate (This Week)
- [ ] Complete Session 1: Extract 10 questions
- [ ] Document tagging conventions
- [ ] Validate template with real data

### Phase 1 (Weeks 1-2)
- [ ] Extract 100 gold-standard questions manually
- [ ] Establish quality benchmark
- [ ] Create tagging guidelines

### Phase 2 (Weeks 3-8)
- [ ] Build AI extraction tool (Claude API)
- [ ] Extract 1,000 questions with human review
- [ ] Refine prompts and validation

### Phase 3 (Weeks 9-16)
- [ ] Scale to 40,000+ questions
- [ ] Quality sampling (10% review)
- [ ] Complete Question Bank RAG

See `NEXT-STEPS-QUESTION-EXTRACTION.md` for detailed roadmap.

---

## 🔗 Related Files

- **Intelligence System**: `../.claude/rules/content-generation.md` - Full adaptive learning architecture
- **System Design**: `../VISION.md` - Overall Edulume vision
- **Collection History**: `COLLECTION-GUIDE.md` - Detailed collection log

---

## 💡 Key Concepts

**Vertical Level**: Student's overall mastery (0-8)
**Horizontal Level**: Difficulty within vertical (1-4)
**Cognitive Type**: Bloom's taxonomy classification
**Solution**: Full step-by-step explanation (most critical field)

---

Last Updated: 2025-03-04
