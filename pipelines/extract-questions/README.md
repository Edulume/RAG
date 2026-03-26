# Question Bank Automation

AI-powered question extraction using Claude Sonnet 4.5 Vision API.

## Quick Start

### 1. Install Dependencies

```bash
cd scripts/automation
bun install
```

### 2. Install System Requirements

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

### 3. Set Up Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API key
nano .env
```

Required: `ANTHROPIC_API_KEY=your_key_here`

### 4. Run Extraction

**Extract from specific PDFs:**
```bash
# Extract from NCERT Exemplar Class 10 Math
bun run extract "NCERT-Exemplar/Class-10/Mathematics/*.pdf"

# Extract from all JEE Main papers
bun run extract "JEE-PYQ/JEE-Main/*.pdf"

# Extract from a single PDF
bun run extract "NCERT-Exemplar/Class-10/Mathematics/Chapter-02.pdf"
```

**Extract from all PDFs:**
```bash
bun run extract "**/*.pdf"
```

## How It Works

```
PDF → Image Conversion → Claude Vision API → JSON Validation → CSV Append
```

1. **PDF Converter**: Converts PDF pages to images using Poppler
2. **Few-Shot Loader**: Loads 76 gold-standard questions as examples
3. **Claude Extractor**: Sends images to Claude Sonnet 4.5 with prompt
4. **CSV Writer**: Validates and appends extracted questions to master CSV

## Output

- **CSV File**: `../../question-bank-template.csv` (appends to existing)
- **Logs**: `./logs/extraction-{date}-{session}.log`
- **Errors**: `./logs/errors-{date}-{session}.log`

## Configuration

Edit `.env` to customize:

- `MODEL`: Claude model to use (default: claude-sonnet-4-5-20250929)
- `MAX_CONCURRENT_REQUESTS`: API concurrency (default: 3)
- `BATCH_SIZE`: Pages per batch (default: 5)

## Cost Tracking

The script tracks API usage and costs in real-time:

- Input tokens: $3 per 1M tokens
- Output tokens: $15 per 1M tokens
- Average: ~$0.003-0.005 per question

Expected costs:
- 1,000 questions: ~$3-5
- 10,000 questions: ~$30-50
- 100,000 questions: ~$300-500

## Quality Control

Each extracted question is validated against schema:
- All 16 required fields present
- Vertical level: 0-8
- Horizontal level: 1-4
- Solution: minimum 100 characters
- Question ID format: `Q_{SOURCE}_{CLASS}_{SUBJECT}_{CHAPTER}_{NUMBER}`

Invalid questions are logged but not written to CSV.

## Troubleshooting

**"pdftoppm: command not found"**
→ Install Poppler: `brew install poppler`

**"ANTHROPIC_API_KEY not set"**
→ Create `.env` file with your API key

**"No PDFs found"**
→ Check your glob pattern and PDF directory path

**High costs**
→ Consider switching to Claude Haiku in `.env`: `MODEL=claude-haiku-20250305`

## Directory Structure

```
automation/
├── src/
│   ├── modules/          # Core extraction modules
│   │   ├── pdf-converter.ts
│   │   ├── few-shot-loader.ts
│   │   ├── claude-extractor.ts
│   │   └── csv-writer.ts
│   ├── config/           # Configuration & types
│   │   ├── settings.ts
│   │   └── types.ts
│   ├── utils/            # Utilities
│   │   └── logger.ts
│   └── main.ts           # Entry point
├── logs/                 # Extraction logs
├── temp/                 # Temporary image files
└── output/               # Backup outputs
```

## Next Steps

After extraction:
1. Review logs for errors
2. Spot-check 10% of extracted questions
3. Fix systematic errors by updating prompt
4. Re-run on failed PDFs

## Support

See `../../AUTOMATION-PLAN.md` for full technical documentation.
