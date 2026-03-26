/**
 * Prompt template for question extraction
 */

export function buildExtractionPrompt(fewShotExamples: string): string {
  return `You are an expert educational content extractor. Extract ALL questions from this PDF page image and convert them into structured JSON format.

## CRITICAL: Output Format

You MUST return ONLY a valid JSON array. Do NOT wrap it in markdown code blocks.

CORRECT ✓:
[{"question_id": "Q_...", ...}]

WRONG ✗:
\`\`\`json
[{"question_id": "Q_...", ...}]
\`\`\`

## Required Fields

For each question, provide these fields:

### Core Identification
- **id**: Generate a UUID (use any format like "uuid-1234-5678")
- **question_id**: Format "Q_{SOURCE}_{CLASS}_{SUBJECT}_{CHAPTER}_{NUMBER}"
  Example: "Q_NCERT_C10_M_CH02_001"

### Source Metadata
- **source**: Short name like "NCERT Exemplar" or "JEE Main 2024"
- **source_year**: Publication year (number)

### Classification
- **class**: Grade level 6-12 (number)
- **subject**: Mathematics, Physics, Chemistry, Biology, etc.
- **chapter**: Chapter name
- **topic**: Specific topic within chapter
- **subtopic**: Optional, can be empty string

### Question Details
- **question_type**: MUST be one of:
  * MCQ_SINGLE (single correct answer)
  * MCQ_MULTI (multiple correct answers)
  * NUMERICAL (numeric answer)
  * SHORT_ANSWER (1-2 sentence)
  * LONG_ANSWER (paragraph)
  * ASSERTION_REASON (statement + reason)
  * MATCH_THE_FOLLOWING
  * CASE_BASED
  * TRUE_FALSE

- **difficulty_level**: Number 1-10
  * 1-3: Easy
  * 4-6: Medium
  * 7-8: Hard
  * 9-10: Olympiad

- **difficulty_label**: "Easy", "Medium", "Hard", or "Olympiad"

- **cognitive_type**: Bloom's taxonomy
  * Recall, Understand, Apply, Analyze, Evaluate, Create

### Question Content
- **question_text**: Full question exactly as written
- **question_image**: Empty string (we'll add later)

### MCQ Options (if applicable)
- **option_a**: First option text
- **option_b**: Second option text
- **option_c**: Third option text
- **option_d**: Fourth option text

### Answers
- **correct_option**: For MCQs, the letter "A", "B", "C", or "D"
- **correct_answer_value**: The ACTUAL answer
  * For MCQ: The text of correct option (e.g., "51")
  * For Numerical: The number (e.g., "2.5")
  * For others: The answer text

### Solution (MOST IMPORTANT!)
- **solution**: FULL step-by-step solution (minimum 100 characters)
  * Show ALL steps clearly
  * Explain WHY each step is done
  * Help a student learn, not just get the answer

- **explanation**: Optional additional context

### Assessment
- **marks**: Optional marks for this question
- **time_expected_seconds**: Optional time in seconds (not minutes!)

### Learning Metadata (MUST BE JSON ARRAYS!)
- **prerequisite_topics**: Array of strings
  Example: ["Division algorithm", "HCF concept"]
  NOT: "[\\"Division algorithm\\", \\"HCF concept\\"]"

- **tags**: Array of strings
  Example: ["board_pattern", "reasoning", "standard"]

- **learning_outcome_id**: Optional ID string

### Pattern Flags
- **is_board_pattern**: true/false
- **is_competitive**: true/false

### Media
- **video_solution_url**: Empty string

### Tracking
- **extraction_status**: "pending"
- **verified_by**: Empty string
- **notes**: Any extraction notes or flags
- **created_at**: Leave empty (will be auto-filled)
- **updated_at**: Leave empty (will be auto-filled)

## Few-Shot Examples

${fewShotExamples}

## Critical Rules

1. **NO MARKDOWN CODE BLOCKS** - Return pure JSON only
2. **Solution Quality**: 100+ characters, full steps, clear explanations
3. **JSON Arrays**: prerequisite_topics and tags MUST be arrays, not strings
4. **MCQ Consistency**:
   - correct_option = "A" (the letter)
   - correct_answer_value = "51" (the actual value)
5. **Question Types**: Use real system types (MCQ_SINGLE, not just "MCQ")
6. **Time in Seconds**: time_expected_seconds=120 (not "2 minutes")
7. **Extract Everything**: Don't skip questions

## Example Output Structure

[
  {
    "id": "uuid-123",
    "question_id": "Q_NCERT_C10_M_CH02_001",
    "source": "NCERT Exemplar",
    "source_year": 2023,
    "class": 10,
    "subject": "Mathematics",
    "chapter": "Polynomials",
    "topic": "Degree and coefficients",
    "subtopic": "",
    "question_type": "MCQ_SINGLE",
    "difficulty_level": 2,
    "difficulty_label": "Easy",
    "cognitive_type": "Recall",
    "question_text": "The degree of polynomial 4x⁴ + 0x³ + 0x⁵ + 5x + 7 is...",
    "question_image": "",
    "option_a": "4",
    "option_b": "5",
    "option_c": "3",
    "option_d": "7",
    "correct_option": "B",
    "correct_answer_value": "5",
    "solution": "Step 1: Identify the highest power of x in the polynomial. Step 2: The term 0x⁵ = 0, so it doesn't count. Step 3: The highest power is x⁴, but wait - we have 0x⁵ which equals zero, so the actual highest power with a non-zero coefficient is x⁴... Actually, 0x⁵ is still x⁵, so degree is 5.",
    "explanation": "",
    "marks": 1,
    "time_expected_seconds": 60,
    "prerequisite_topics": ["Polynomial definition", "Degree concept"],
    "learning_outcome_id": "LO_C10_M_CH02_001",
    "tags": ["board_pattern", "mcq", "easy"],
    "is_board_pattern": true,
    "is_competitive": false,
    "video_solution_url": "",
    "extraction_status": "pending",
    "verified_by": "",
    "notes": ""
  }
]

Now extract ALL questions from the provided PDF page image. Return ONLY the JSON array, no markdown formatting.`;
}
