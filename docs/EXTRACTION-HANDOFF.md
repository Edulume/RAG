# Question Bank Extraction - Session Handoff

## GIVE THIS TO CLAUDE ON SESSION RESTART

---

## Current Task
Extracting questions from PDF question banks using Claude's vision capabilities directly (not Anthropic API).

## How To Continue

1. **Check current progress:**
```bash
cat /Users/rahulsain/Documents/kzr/Edulume/intelligence/rag/extraction-log.csv
```

2. **Find next PDF to process:**
```bash
# NCERT Exemplar Class-12 Math (current priority)
ls /Users/rahulsain/Documents/kzr/Edulume/intelligence/rag/data/question-bank/NCERT-Exemplar/Class-12/Mathematics/
```

3. **Read PDF and extract questions, then append to CSV:**
```
Output file: /Users/rahulsain/Documents/kzr/Edulume/intelligence/rag/question-bank-template.csv
```

## Extraction Order (Priority)
1. NCERT Exemplar Class-12 Math - COMPLETE (All 13 chapters)
2. NCERT Exemplar Class-12 Physics - COMPLETE (All 15 chapters)
3. NCERT Exemplar Class-12 Chemistry - NEXT
4. NCERT Exemplar Class-12 Biology
5. NCERT Exemplar Class-11 (all subjects)
6. NCERT Exemplar Class-10 (all subjects)
7. JEE-PYQ
8. NEET-PYQ
9. CBSE-PYQ

## Already Completed

### NCERT Exemplar Class-12 Mathematics (COMPLETE)
- Class-12/Math/Chapter-01.pdf: 28 questions (Relations and Functions)
- Class-12/Math/Chapter-02.pdf: 55 questions (Inverse Trigonometric Functions)
- Class-12/Math/Chapter-03.pdf: 154 questions (Matrices)
- Class-12/Math/Chapter-04.pdf: 111 questions (Determinants)
- Class-12/Math/Chapter-05.pdf: 106 questions (Continuity and Differentiability)
- Class-12/Math/Chapter-06.pdf: 64 questions (Application of Derivatives)
- Class-12/Math/Chapter-07.pdf: 63 questions (Integrals)
- Class-12/Math/Chapter-08.pdf: 34 questions (Application of Integrals)
- Class-12/Math/Chapter-09.pdf: 97 questions (Differential Equations)
- Class-12/Math/Chapter-10.pdf: 45 questions (Vector Algebra)
- Class-12/Math/Chapter-11.pdf: 49 questions (Three Dimensional Geometry)
- Class-12/Math/Chapter-12.pdf: 45 questions (Linear Programming)
- Class-12/Math/Chapter-13.pdf: 108 questions (Probability)
- **Math Total: 959 questions**

### NCERT Exemplar Class-12 Physics (COMPLETE)
- Class-12/Physics/Chapter-01.pdf: 31 questions (Electric Charges and Fields) ✓
- Class-12/Physics/Chapter-02.pdf: 33 questions (Electrostatic Potential and Capacitance) ✓
- Class-12/Physics/Chapter-03.pdf: 31 questions (Current Electricity) ✓
- Class-12/Physics/Chapter-04.pdf: 29 questions (Moving Charges and Magnetism) ✓
- Class-12/Physics/Chapter-05.pdf: 25 questions (Magnetism and Matter) ✓
- Class-12/Physics/Chapter-06.pdf: 32 questions (Electromagnetic Induction) ✓
- Class-12/Physics/Chapter-07.pdf: 31 questions (Alternating Current) ✓
- Class-12/Physics/Chapter-08.pdf: 32 questions (Electromagnetic Waves) ✓
- Class-12/Physics/Chapter-09.pdf: 32 questions (Ray Optics and Optical Instruments) ✓
- Class-12/Physics/Chapter-10.pdf: 23 questions (Wave Optics) ✓
- Class-12/Physics/Chapter-11.pdf: 29 questions (Dual Nature of Radiation and Matter) ✓
- Class-12/Physics/Chapter-12.pdf: 29 questions (Atoms) ✓
- Class-12/Physics/Chapter-13.pdf: 26 questions (Nuclei) ✓
- Class-12/Physics/Chapter-14.pdf: 40 questions (Semiconductor Electronics) ✓
- Class-12/Physics/Chapter-15.pdf: 30 questions (Communication Systems) ✓
- **Physics Total: 453 questions (15/15 chapters)**

### Grand Total: 1412 questions

## Question Schema (CSV Columns)
```
question_id,source_book,source_year,class,subject,chapter,topic,subtopic,skill,question_type,
vertical_level,horizontal_level,cognitive_type,question_text,option_a,option_b,option_c,option_d,
correct_answer,solution,explanation,marks,time_expected,prerequisite_topics,learning_outcome_id,
tags,difficulty_rating,is_board_pattern,is_competitive,image_path,video_solution_url,
created_at,updated_at,extraction_status,verified_by,notes
```

## V×H Ranges for NCERT Exemplar
- **source_book**: "NCERT Exemplar"
- **source_type**: foundational
- **vertical_level**: 1-3
- **horizontal_level**: 1-3

## Question ID Format
`Q_NCERT_C{class}_{subject_initial}_{chapter}_{number}`
Example: Q_NCERT_C12_M_CH05_001

## Question Types
- MCQ_SINGLE, MCQ_MULTI, MCQ
- NUMERICAL, SHORT_ANSWER, LONG_ANSWER
- ASSERTION_REASON, MATCH_THE_FOLLOWING, CASE_BASED, TRUE_FALSE

## Instructions for Claude
1. Read the PDF file using Read tool
2. Extract ALL questions with full solutions
3. For each question, provide:
   - Complete question text
   - All options (for MCQs)
   - Correct answer
   - Step-by-step solution
   - Topic/subtopic identification
4. Append to CSV using proper escaping
5. Update extraction-log.csv with status
6. Give summary after each PDF
## Progress Tracking
After each PDF, update:
- extraction-log.csv (add row)
- Report to user: "Extracted X questions from [PDF]. Total: Y questions"
