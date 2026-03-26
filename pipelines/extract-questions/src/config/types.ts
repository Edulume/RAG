/**
 * Type definitions for question bank schema
 * Field names match CSV column names exactly
 */

import { z } from 'zod';

// Cognitive types based on Bloom's taxonomy
export const CognitiveType = z.enum([
  'Recall',
  'Understand',
  'Apply',
  'Analyze',
  'Evaluate',
  'Create',
]);

// Question types (real system types)
export const QuestionType = z.enum([
  'MCQ_SINGLE',
  'MCQ_MULTI',
  'MCQ',
  'NUMERICAL',
  'SHORT_ANSWER',
  'LONG_ANSWER',
  'ASSERTION_REASON',
  'MATCH_THE_FOLLOWING',
  'CASE_BASED',
  'TRUE_FALSE',
]);

// Source types for adaptive learning matrix
export const SourceType = z.enum([
  'foundational', // NCERT, NCERT Exemplar
  'practice', // CBSE Sample Papers
  'reference', // Pradeep, Oswaal, RD Sharma, HC Verma
  'pyq', // CBSE PYQ
  'competitive', // JEE Main, JEE Advanced, NEET, Olympiad
]);

// Extraction status
export const ExtractionStatus = z.enum([
  'pending',
  'extracted',
  'verified',
  'needs_review',
  'error',
]);

// Question schema - field names match CSV columns exactly
export const QuestionSchema = z.object({
  // Core identification
  question_id: z.string(), // Human-readable ID like Q_NCERT_C10_M_CH02_005

  // Source metadata (CSV column: source_book)
  source_book: z.string(), // "NCERT Exemplar" or "JEE Main" etc.
  source_year: z.union([z.number(), z.string()]).optional(),

  // Classification
  class: z.union([z.number(), z.string()]).optional(),
  subject: z.string(),
  chapter: z.string(),
  topic: z.string(),
  subtopic: z.string().optional().default(''),
  skill: z.string().optional().default(''), // Skill being tested

  // Question details
  question_type: z.string(), // Flexible to allow various types
  vertical_level: z.number().min(0).max(8), // Student mastery level (0=Beginner, 8=Master)
  horizontal_level: z.number().min(1).max(8), // Source progression (1-2=NCERT, 7-8=PYQ/Competitive)
  cognitive_type: z.string().optional().default('Apply'),

  // Question content
  question_text: z.string().min(10),

  // MCQ options
  option_a: z.string().optional().default(''),
  option_b: z.string().optional().default(''),
  option_c: z.string().optional().default(''),
  option_d: z.string().optional().default(''),

  // Answer (CSV column: correct_answer)
  correct_answer: z.string(), // The actual answer text/value or option letter

  // Solution
  solution: z.string().min(50),
  explanation: z.string().optional().default(''),

  // Assessment metadata (CSV column: time_expected)
  marks: z.union([z.number(), z.string()]).optional(),
  time_expected: z.union([z.number(), z.string()]).optional(),

  // Learning metadata
  prerequisite_topics: z.array(z.string()).optional().default([]),
  learning_outcome_id: z.string().optional().default(''),
  tags: z.array(z.string()).optional().default([]),

  // Difficulty (CSV column: difficulty_rating)
  difficulty_rating: z.union([z.number(), z.string()]).optional(),

  // Pattern flags
  is_board_pattern: z.union([z.boolean(), z.string()]).optional(),
  is_competitive: z.union([z.boolean(), z.string()]).optional(),

  // Media (CSV column: image_path)
  image_path: z.string().optional().default(''),
  video_solution_url: z.string().optional().default(''),

  // Tracking
  created_at: z.string().optional().default(''),
  updated_at: z.string().optional().default(''),
  extraction_status: z.string().optional().default('extracted'),
  verified_by: z.string().optional().default(''),
  notes: z.string().optional().default(''),
});

export type Question = z.infer<typeof QuestionSchema>;

// Batch extraction result
export interface ExtractionResult {
  success: boolean;
  questions: Question[];
  errors: string[];
  metadata: {
    pdfPath: string;
    pageNumber: number;
    processingTime: number;
    tokenUsage?: {
      input: number;
      output: number;
    };
  };
}

// Few-shot example from gold standard
export interface FewShotExample {
  question: Question;
  context: string; // Description of why this is a good example
}

// V×H Range configuration for each source type
export const VH_RANGES: Record<
  string,
  {
    source_type: z.infer<typeof SourceType>;
    vertical: { min: number; max: number };
    horizontal: { min: number; max: number };
  }
> = {
  // Foundational sources
  NCERT: {
    source_type: 'foundational',
    vertical: { min: 0, max: 2 },
    horizontal: { min: 1, max: 2 },
  },
  'NCERT Exemplar': {
    source_type: 'foundational',
    vertical: { min: 1, max: 3 },
    horizontal: { min: 1, max: 3 },
  },

  // Practice sources
  'CBSE Sample Paper': {
    source_type: 'practice',
    vertical: { min: 2, max: 4 },
    horizontal: { min: 3, max: 4 },
  },

  // Reference sources
  Pradeep: {
    source_type: 'reference',
    vertical: { min: 3, max: 5 },
    horizontal: { min: 5, max: 6 },
  },
  Oswaal: {
    source_type: 'reference',
    vertical: { min: 3, max: 5 },
    horizontal: { min: 5, max: 6 },
  },
  'RD Sharma': {
    source_type: 'reference',
    vertical: { min: 3, max: 5 },
    horizontal: { min: 5, max: 6 },
  },
  'HC Verma': {
    source_type: 'reference',
    vertical: { min: 4, max: 6 },
    horizontal: { min: 5, max: 6 },
  },
  Arihant: {
    source_type: 'reference',
    vertical: { min: 3, max: 5 },
    horizontal: { min: 5, max: 6 },
  },

  // PYQ sources
  'CBSE PYQ': {
    source_type: 'pyq',
    vertical: { min: 4, max: 6 },
    horizontal: { min: 7, max: 8 },
  },
  'State Board PYQ': {
    source_type: 'pyq',
    vertical: { min: 4, max: 6 },
    horizontal: { min: 7, max: 8 },
  },

  // Competitive sources
  'JEE Main': {
    source_type: 'competitive',
    vertical: { min: 7, max: 7 },
    horizontal: { min: 7, max: 8 },
  },
  NEET: {
    source_type: 'competitive',
    vertical: { min: 7, max: 7 },
    horizontal: { min: 7, max: 8 },
  },
  'JEE Advanced': {
    source_type: 'competitive',
    vertical: { min: 8, max: 8 },
    horizontal: { min: 7, max: 8 },
  },
  Olympiad: {
    source_type: 'competitive',
    vertical: { min: 8, max: 8 },
    horizontal: { min: 8, max: 8 },
  },
};

// Helper to get V×H range from source name
export function getVHRange(sourceName: string): {
  source_type: z.infer<typeof SourceType>;
  vertical: { min: number; max: number };
  horizontal: { min: number; max: number };
} {
  // Try exact match first
  if (VH_RANGES[sourceName]) {
    return VH_RANGES[sourceName];
  }

  // Try partial match - sort by key length descending to prefer more specific matches
  const sortedKeys = Object.keys(VH_RANGES).sort((a, b) => b.length - a.length);
  const sourceKey = sortedKeys.find(
    key =>
      sourceName.toLowerCase().includes(key.toLowerCase()) ||
      key.toLowerCase().includes(sourceName.toLowerCase())
  );

  if (sourceKey) {
    return VH_RANGES[sourceKey];
  }

  // Default to NCERT Exemplar range for unknown sources
  return VH_RANGES['NCERT Exemplar'];
}
