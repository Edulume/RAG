/**
 * Prompt templates for question extraction
 * 5 specialized templates for different source types in the V×H adaptive learning matrix
 */

// Common schema documentation shared across all templates
const SCHEMA_DOCS = `## Required Fields

For each question, provide these fields:

### Core Identification
- **id**: Generate a UUID (use any format like "uuid-1234-5678")
- **question_id**: Format "Q_{SOURCE}_{CLASS}_{SUBJECT}_{CHAPTER}_{NUMBER}"
  Example: "Q_NCERT_C10_M_CH02_001"

### Source Metadata
- **source**: Short name like "NCERT Exemplar" or "JEE Main 2024"
- **source_year**: Publication year (number)

### Adaptive Learning Matrix (V×H System) - CRITICAL!
- **vertical_level**: Student mastery level (0-8)
- **horizontal_level**: Source difficulty tier (1-8)
- **source_type**: One of "foundational", "practice", "reference", "pyq", "competitive"

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

- **difficulty_rating**: Number 1-10
  * 1-3: Easy
  * 4-6: Medium
  * 7-8: Hard
  * 9-10: Olympiad

- **difficulty_label**: "Easy", "Medium", "Hard", or "Olympiad"

- **cognitive_type**: Bloom's taxonomy
  * Recall, Understand, Apply, Analyze, Evaluate, Create

### Question Content
- **question_text**: Full question exactly as written
- **image_path**: Empty string (we'll add later)

### MCQ Options (if applicable)
- **option_a**: First option text
- **option_b**: Second option text
- **option_c**: Third option text
- **option_d**: Fourth option text

### Answers
- **correct_option**: For MCQs, the letter "A", "B", "C", or "D"
- **correct_answer**: The ACTUAL answer
  * For MCQ: The text of correct option (e.g., "51")
  * For Numerical: The number (e.g., "2.5")
  * For others: The answer text

### Solution (MOST IMPORTANT!)
- **solution**: FULL step-by-step solution (minimum 50 characters)
  * Show ALL steps clearly
  * Explain WHY each step is done
  * Help a student learn, not just get the answer

- **explanation**: Optional additional context

### Assessment
- **marks**: Optional marks for this question
- **time_expected**: Optional time in seconds (not minutes!)

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
- **updated_at**: Leave empty (will be auto-filled)`;

const CRITICAL_RULES = `## Critical Rules

1. **NO MARKDOWN CODE BLOCKS** - Return pure JSON only
2. **Solution Quality**: 50+ characters, full steps, clear explanations
3. **JSON Arrays**: prerequisite_topics and tags MUST be arrays, not strings
4. **MCQ Consistency**:
   - correct_option = "A" (the letter)
   - correct_answer = "51" (the actual value)
5. **Question Types**: Use real system types (MCQ_SINGLE, not just "MCQ")
6. **Time in Seconds**: time_expected=120 (not "2 minutes")
7. **Extract Everything**: Don't skip questions
8. **V×H Assignment**: Follow the V×H ranges specified for this source type`;

const OUTPUT_FORMAT = `## CRITICAL: Output Format

You MUST return ONLY a valid JSON array. Do NOT wrap it in markdown code blocks.

CORRECT ✓:
[{"question_id": "Q_...", ...}]

WRONG ✗:
\`\`\`json
[{"question_id": "Q_...", ...}]
\`\`\``;

/**
 * Template 1: NCERT and NCERT Exemplar
 * Sources: NCERT, NCERT Exemplar
 * V×H Range: V0-V3, H1-H3
 * source_type: foundational
 */
export function buildNCERTTemplate(fewShotExamples: string): string {
  return `You are an expert educational content extractor specializing in NCERT textbooks and Exemplar problems. Extract ALL questions from this PDF page image.

## Source Type: FOUNDATIONAL (NCERT/NCERT Exemplar)

This is foundational educational content. Questions build core understanding.

## V×H Assignment Rules (CRITICAL!)

For NCERT and NCERT Exemplar:
- **source_type**: "foundational" (ALWAYS)
- **vertical_level**: Assign based on question complexity:
  * 0-1: Basic recall, definitions, simple calculations
  * 2: Application of single concept
  * 3: Multi-step problems requiring deeper understanding
- **horizontal_level**: Assign based on source:
  * 1-2: Pure NCERT textbook questions
  * 2-3: NCERT Exemplar questions (slightly harder)

| Source | vertical_level | horizontal_level |
|--------|---------------|------------------|
| NCERT | 0-2 | 1-2 |
| NCERT Exemplar | 1-3 | 1-3 |

${OUTPUT_FORMAT}

${SCHEMA_DOCS}

## Few-Shot Examples

${fewShotExamples}

${CRITICAL_RULES}

## Example with V×H Assignment

[
  {
    "id": "uuid-123",
    "question_id": "Q_NCERT_C10_M_CH02_001",
    "source_book": "NCERT Exemplar",
    "source_year": 2023,
    "vertical_level": 2,
    "horizontal_level": 2,
    "source_type": "foundational",
    "class": 10,
    "subject": "Mathematics",
    "chapter": "Polynomials",
    "topic": "Degree and coefficients",
    "subtopic": "",
    "question_type": "MCQ_SINGLE",
    "difficulty_rating": 3,
    "difficulty_label": "Easy",
    "cognitive_type": "Understand",
    "question_text": "The degree of polynomial 4x⁴ + 0x³ + 0x⁵ + 5x + 7 is...",
    "image_path": "",
    "option_a": "4",
    "option_b": "5",
    "option_c": "3",
    "option_d": "7",
    "correct_option": "B",
    "correct_answer": "5",
    "solution": "Step 1: Identify all terms in the polynomial: 4x⁴, 0x³, 0x⁵, 5x, and 7. Step 2: Note that 0x⁵ = 0 and 0x³ = 0, so these terms vanish. Step 3: The remaining terms are 4x⁴, 5x, and 7. Step 4: The highest power with a non-zero coefficient is x⁴, so the degree is 4. Wait, let me reconsider - 0x⁵ is written but equals zero, so it doesn't contribute. The degree is 4, not 5. But the question might be testing if students recognize that writing a term with 0 coefficient doesn't change the degree.",
    "explanation": "A common trap question testing understanding of zero coefficients",
    "marks": 1,
    "time_expected": 60,
    "prerequisite_topics": ["Polynomial definition", "Degree concept"],
    "learning_outcome_id": "LO_C10_M_CH02_001",
    "tags": ["ncert", "conceptual", "easy"],
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

/**
 * Template 2: Reference Books
 * Sources: Pradeep, Oswaal, RD Sharma, HC Verma, Arihant
 * V×H Range: V3-V6, H5-H6
 * source_type: reference
 */
export function buildReferenceTemplate(fewShotExamples: string): string {
  return `You are an expert educational content extractor specializing in reference textbooks for competitive exam preparation. Extract ALL questions from this PDF page image.

## Source Type: REFERENCE (Pradeep, Oswaal, RD Sharma, HC Verma, Arihant)

These are comprehensive reference books with in-depth problem coverage. Questions test deep conceptual understanding and problem-solving skills.

## V×H Assignment Rules (CRITICAL!)

For Reference Books:
- **source_type**: "reference" (ALWAYS)
- **vertical_level**: Assign based on question complexity:
  * 3: Standard application problems
  * 4: Multi-concept problems
  * 5: Advanced reasoning and derivations
  * 6: Only for HC Verma difficult problems
- **horizontal_level**:
  * 5: Standard reference book questions
  * 6: Challenge/Advanced sections

| Source | vertical_level | horizontal_level |
|--------|---------------|------------------|
| Pradeep | 3-5 | 5-6 |
| Oswaal | 3-5 | 5-6 |
| RD Sharma | 3-5 | 5-6 |
| HC Verma | 4-6 | 5-6 |
| Arihant | 3-5 | 5-6 |

${OUTPUT_FORMAT}

${SCHEMA_DOCS}

## Few-Shot Examples

${fewShotExamples}

${CRITICAL_RULES}

## Example with V×H Assignment

[
  {
    "id": "uuid-456",
    "question_id": "Q_HCV_C11_P_CH04_015",
    "source_book": "HC Verma",
    "source_year": 2023,
    "vertical_level": 5,
    "horizontal_level": 6,
    "source_type": "reference",
    "class": 11,
    "subject": "Physics",
    "chapter": "Newton's Laws of Motion",
    "topic": "Friction",
    "subtopic": "Limiting friction",
    "question_type": "NUMERICAL",
    "difficulty_rating": 7,
    "difficulty_label": "Hard",
    "cognitive_type": "Analyze",
    "question_text": "A block of mass 2 kg is placed on a rough inclined plane making an angle of 30° with the horizontal. The coefficient of static friction is 0.5. Find the minimum force parallel to the incline needed to start moving the block up the incline.",
    "image_path": "",
    "option_a": "",
    "option_b": "",
    "option_c": "",
    "option_d": "",
    "correct_option": "",
    "correct_answer": "18.66 N",
    "solution": "Step 1: Identify forces acting on the block - Weight mg = 2 × 10 = 20 N, Normal force N, Friction force f, Applied force F (up the incline). Step 2: Resolve weight into components - mg sin 30° = 10 N (down the incline), mg cos 30° = 17.32 N (perpendicular to incline). Step 3: Normal force N = mg cos 30° = 17.32 N. Step 4: Maximum static friction f_s = μN = 0.5 × 17.32 = 8.66 N (acts down the incline when block is about to move up). Step 5: For block to just start moving up: F = mg sin 30° + f_s = 10 + 8.66 = 18.66 N.",
    "explanation": "Classic inclined plane problem combining resolution of forces with friction analysis",
    "marks": 4,
    "time_expected": 300,
    "prerequisite_topics": ["Free body diagram", "Resolution of forces", "Friction coefficient"],
    "learning_outcome_id": "LO_C11_P_CH04_003",
    "tags": ["hcv", "mechanics", "numerical", "friction"],
    "is_board_pattern": false,
    "is_competitive": true,
    "video_solution_url": "",
    "extraction_status": "pending",
    "verified_by": "",
    "notes": ""
  }
]

Now extract ALL questions from the provided PDF page image. Return ONLY the JSON array, no markdown formatting.`;
}

/**
 * Template 3: CBSE PYQ and Sample Papers
 * Sources: CBSE PYQ, State Board PYQ, CBSE Sample Papers
 * V×H Range: V2-V6, H3-H4 (samples), H7-H8 (PYQs)
 * source_type: practice or pyq
 */
export function buildPYQTemplate(fewShotExamples: string): string {
  return `You are an expert educational content extractor specializing in board examination papers. Extract ALL questions from this PDF page image.

## Source Type: PYQ/PRACTICE (CBSE PYQ, Sample Papers)

These are actual board examination questions and sample papers. Questions follow CBSE marking scheme and exam patterns.

## V×H Assignment Rules (CRITICAL!)

For CBSE Papers:
- **source_type**:
  * "practice" for Sample Papers
  * "pyq" for actual Previous Year Questions
- **vertical_level**: Assign based on question complexity:
  * 2-3: 1-mark questions (recall/basic application)
  * 4: 2-3 mark questions (application)
  * 5-6: 4-5 mark questions (analysis/evaluation)
- **horizontal_level**:
  * 3-4: Sample Papers (slightly easier)
  * 7-8: Actual PYQs (exam standard)

| Source | source_type | vertical_level | horizontal_level |
|--------|-------------|---------------|------------------|
| CBSE Sample Paper | practice | 2-4 | 3-4 |
| CBSE PYQ | pyq | 4-6 | 7-8 |
| State Board PYQ | pyq | 4-6 | 7-8 |

${OUTPUT_FORMAT}

${SCHEMA_DOCS}

## Few-Shot Examples

${fewShotExamples}

${CRITICAL_RULES}

## Example with V×H Assignment

[
  {
    "id": "uuid-789",
    "question_id": "Q_CBSE_C12_M_2024_S1_023",
    "source_book": "CBSE PYQ",
    "source_year": 2024,
    "vertical_level": 5,
    "horizontal_level": 7,
    "source_type": "pyq",
    "class": 12,
    "subject": "Mathematics",
    "chapter": "Integrals",
    "topic": "Integration by parts",
    "subtopic": "",
    "question_type": "LONG_ANSWER",
    "difficulty_rating": 6,
    "difficulty_label": "Medium",
    "cognitive_type": "Apply",
    "question_text": "Evaluate: ∫ x² log x dx",
    "image_path": "",
    "option_a": "",
    "option_b": "",
    "option_c": "",
    "option_d": "",
    "correct_option": "",
    "correct_answer": "(x³/3)log x - x³/9 + C",
    "solution": "Step 1: Use integration by parts formula: ∫u dv = uv - ∫v du. Step 2: Choose u = log x (logarithmic) and dv = x² dx (algebraic) following LIATE rule. Step 3: Then du = (1/x)dx and v = x³/3. Step 4: Apply formula: ∫x² log x dx = (x³/3)(log x) - ∫(x³/3)(1/x)dx. Step 5: Simplify: = (x³/3)log x - (1/3)∫x² dx. Step 6: Integrate: = (x³/3)log x - (1/3)(x³/3) + C. Step 7: Final answer: = (x³/3)log x - x³/9 + C.",
    "explanation": "Standard CBSE board question on integration by parts following LIATE rule",
    "marks": 4,
    "time_expected": 480,
    "prerequisite_topics": ["Integration by parts", "LIATE rule", "Logarithmic differentiation"],
    "learning_outcome_id": "LO_C12_M_CH07_005",
    "tags": ["cbse_pyq", "integration", "4_marks", "board_pattern"],
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

/**
 * Template 4: JEE Main and NEET
 * Sources: JEE Main, NEET
 * V×H Range: V7, H7-H8
 * source_type: competitive
 */
export function buildJEENEETTemplate(fewShotExamples: string): string {
  return `You are an expert educational content extractor specializing in competitive entrance examinations. Extract ALL questions from this PDF page image.

## Source Type: COMPETITIVE (JEE Main / NEET)

These are competitive entrance exam questions. Questions test application of concepts under time pressure with moderate to high difficulty.

## V×H Assignment Rules (CRITICAL!)

For JEE Main and NEET:
- **source_type**: "competitive" (ALWAYS)
- **vertical_level**: 7 (ALWAYS for JEE Main and NEET)
- **horizontal_level**:
  * 7: Standard difficulty JEE Main/NEET questions
  * 8: High difficulty or multi-concept questions

| Source | vertical_level | horizontal_level |
|--------|---------------|------------------|
| JEE Main | 7 | 7-8 |
| NEET | 7 | 7-8 |

${OUTPUT_FORMAT}

${SCHEMA_DOCS}

## Few-Shot Examples

${fewShotExamples}

${CRITICAL_RULES}

## Example with V×H Assignment

[
  {
    "id": "uuid-jee-001",
    "question_id": "Q_JEE_M_2024_SH1_045",
    "source_book": "JEE Main",
    "source_year": 2024,
    "vertical_level": 7,
    "horizontal_level": 7,
    "source_type": "competitive",
    "class": 12,
    "subject": "Physics",
    "chapter": "Electromagnetic Induction",
    "topic": "Faraday's law",
    "subtopic": "Induced EMF in rotating coil",
    "question_type": "MCQ_SINGLE",
    "difficulty_rating": 7,
    "difficulty_label": "Hard",
    "cognitive_type": "Apply",
    "question_text": "A rectangular coil of N turns and area A is rotating with angular velocity ω in a uniform magnetic field B. The maximum EMF induced in the coil is:",
    "image_path": "",
    "option_a": "NABω",
    "option_b": "NABω/2",
    "option_c": "2NABω",
    "option_d": "NAB/ω",
    "correct_option": "A",
    "correct_answer": "NABω",
    "solution": "Step 1: The magnetic flux through the coil at any instant: Φ = NBA cos(ωt), where the coil rotates with angular velocity ω. Step 2: By Faraday's law, induced EMF: ε = -dΦ/dt = -d(NBA cos ωt)/dt. Step 3: Differentiate: ε = NBAω sin(ωt). Step 4: The maximum value of sin(ωt) is 1. Step 5: Therefore, maximum EMF: ε_max = NBAω = NABω. This is the standard result for EMF in an AC generator.",
    "explanation": "Fundamental AC generator principle tested in JEE Main",
    "marks": 4,
    "time_expected": 120,
    "prerequisite_topics": ["Faraday's law", "Magnetic flux", "Differentiation", "AC generator"],
    "learning_outcome_id": "LO_C12_P_CH06_008",
    "tags": ["jee_main", "emi", "ac_generator", "formula_based"],
    "is_board_pattern": false,
    "is_competitive": true,
    "video_solution_url": "",
    "extraction_status": "pending",
    "verified_by": "",
    "notes": ""
  }
]

Now extract ALL questions from the provided PDF page image. Return ONLY the JSON array, no markdown formatting.`;
}

/**
 * Template 5: JEE Advanced and Olympiad
 * Sources: JEE Advanced, Olympiad, KVPY
 * V×H Range: V8, H7-H8
 * source_type: competitive
 */
export function buildAdvancedTemplate(fewShotExamples: string): string {
  return `You are an expert educational content extractor specializing in advanced competitive examinations. Extract ALL questions from this PDF page image.

## Source Type: COMPETITIVE ADVANCED (JEE Advanced / Olympiad)

These are the highest difficulty questions requiring deep conceptual understanding, multi-step reasoning, and creative problem-solving.

## V×H Assignment Rules (CRITICAL!)

For JEE Advanced and Olympiad:
- **source_type**: "competitive" (ALWAYS)
- **vertical_level**: 8 (ALWAYS - these are master level questions)
- **horizontal_level**:
  * 7: JEE Advanced standard problems
  * 8: Olympiad/hardest JEE Advanced problems

| Source | vertical_level | horizontal_level |
|--------|---------------|------------------|
| JEE Advanced | 8 | 7-8 |
| Olympiad | 8 | 8 |
| KVPY | 8 | 7-8 |

${OUTPUT_FORMAT}

${SCHEMA_DOCS}

## Few-Shot Examples

${fewShotExamples}

${CRITICAL_RULES}

## Example with V×H Assignment

[
  {
    "id": "uuid-adv-001",
    "question_id": "Q_JEE_A_2024_P1_012",
    "source_book": "JEE Advanced",
    "source_year": 2024,
    "vertical_level": 8,
    "horizontal_level": 8,
    "source_type": "competitive",
    "class": 12,
    "subject": "Mathematics",
    "chapter": "Differential Equations",
    "topic": "First order differential equations",
    "subtopic": "Exact differential equations",
    "question_type": "MCQ_MULTI",
    "difficulty_rating": 9,
    "difficulty_label": "Olympiad",
    "cognitive_type": "Analyze",
    "question_text": "Consider the differential equation (2x + y + 1)dx + (x + 2y - 1)dy = 0. Which of the following is/are correct?",
    "image_path": "",
    "option_a": "The equation is exact",
    "option_b": "The general solution passes through (0, 0)",
    "option_c": "The general solution is x² + xy + y² + x - y = c",
    "option_d": "For c = 0, the solution represents a conic section",
    "correct_option": "A,C,D",
    "correct_answer": "The equation is exact; The general solution is x² + xy + y² + x - y = c; For c = 0, the solution represents a conic section",
    "solution": "Step 1: Check if equation is exact. Let M = 2x + y + 1, N = x + 2y - 1. ∂M/∂y = 1, ∂N/∂x = 1. Since ∂M/∂y = ∂N/∂x, the equation is exact. (A is correct) Step 2: Find the solution by integration. ∫M dx = x² + xy + x + f(y). Taking ∂/∂y: x + f'(y) = N = x + 2y - 1. So f'(y) = 2y - 1, giving f(y) = y² - y. Step 3: General solution: x² + xy + x + y² - y = c, or x² + xy + y² + x - y = c. (C is correct) Step 4: Check (0,0): 0 + 0 + 0 + 0 - 0 = c gives c = 0. But this just means c = 0 for this point, not that solution passes through (0,0) for all c. (B needs more analysis - actually for c=0, yes (0,0) satisfies it) Step 5: For c = 0: x² + xy + y² + x - y = 0 is a conic (quadratic in x, y). (D is correct)",
    "explanation": "Multi-concept JEE Advanced problem combining exact differential equations with conic sections",
    "marks": 4,
    "time_expected": 600,
    "prerequisite_topics": ["Exact differential equations", "Partial derivatives", "Integration", "Conic sections"],
    "learning_outcome_id": "LO_C12_M_CH09_012",
    "tags": ["jee_advanced", "differential_equations", "multi_correct", "olympiad_level"],
    "is_board_pattern": false,
    "is_competitive": true,
    "video_solution_url": "",
    "extraction_status": "pending",
    "verified_by": "",
    "notes": ""
  }
]

Now extract ALL questions from the provided PDF page image. Return ONLY the JSON array, no markdown formatting.`;
}

/**
 * Source type detection from PDF path
 */
export type SourceCategory = 'ncert' | 'reference' | 'pyq' | 'jee_neet' | 'advanced';

export function detectSourceCategory(pdfPath: string): SourceCategory {
  const pathLower = pdfPath.toLowerCase();

  // JEE Advanced first (more specific)
  if (pathLower.includes('jee-advanced') || pathLower.includes('jee_advanced') || pathLower.includes('olympiad')) {
    return 'advanced';
  }

  // JEE Main and NEET
  if (
    pathLower.includes('jee-main') ||
    pathLower.includes('jee_main') ||
    pathLower.includes('jee-pyq') ||
    pathLower.includes('neet')
  ) {
    return 'jee_neet';
  }

  // CBSE PYQ
  if (pathLower.includes('cbse-pyq') || pathLower.includes('cbse_pyq') || pathLower.includes('board-pyq')) {
    return 'pyq';
  }

  // Reference books
  if (
    pathLower.includes('pradeep') ||
    pathLower.includes('oswaal') ||
    pathLower.includes('rd-sharma') ||
    pathLower.includes('rd_sharma') ||
    pathLower.includes('hc-verma') ||
    pathLower.includes('hc_verma') ||
    pathLower.includes('arihant') ||
    pathLower.includes('reference')
  ) {
    return 'reference';
  }

  // Default to NCERT (most common)
  return 'ncert';
}

/**
 * Get the appropriate template for a source category
 */
export function getTemplateForSource(
  sourceCategory: SourceCategory,
  fewShotExamples: string
): string {
  switch (sourceCategory) {
    case 'ncert':
      return buildNCERTTemplate(fewShotExamples);
    case 'reference':
      return buildReferenceTemplate(fewShotExamples);
    case 'pyq':
      return buildPYQTemplate(fewShotExamples);
    case 'jee_neet':
      return buildJEENEETTemplate(fewShotExamples);
    case 'advanced':
      return buildAdvancedTemplate(fewShotExamples);
  }
}

/**
 * Legacy function for backward compatibility
 */
export function buildExtractionPrompt(fewShotExamples: string): string {
  return buildNCERTTemplate(fewShotExamples);
}
