/**
 * Configuration settings for question extraction automation
 */

import { resolve } from 'path';

export const config = {
  // API Configuration
  anthropic: {
    apiKey: process.env.ANTHROPIC_API_KEY || '',
    // Model options (all support vision):
    // - claude-3-5-haiku-20241022: Fast & cheap, $0.25/$1.25 per 1M tokens, 8192 max output (RECOMMENDED)
    // - claude-sonnet-4-5-20250929: Best quality, $3/$15 per 1M tokens, 8192 max output
    // - claude-3-haiku-20240307: Legacy Haiku, 4096 max output (DO NOT USE)
    model: process.env.MODEL || 'claude-3-5-haiku-20241022',
    maxTokens: 8192, // Sonnet supports 8192, Haiku only 4096
    temperature: 0.0, // Deterministic for extraction
  },

  // Processing settings
  processing: {
    maxConcurrentRequests: parseInt(process.env.MAX_CONCURRENT_REQUESTS || '3'),
    batchSize: parseInt(process.env.BATCH_SIZE || '5'),
    imageQuality: 85, // JPEG quality for PDF conversion
    imageDPI: 300, // DPI for PDF to image conversion
  },

  // File paths
  paths: {
    ragDir: resolve(process.env.RAG_DIR || '../..'),
    inputPdfDir: resolve(process.env.INPUT_PDF_DIR || '../../data/question-bank'),
    outputCsv: resolve(process.env.OUTPUT_CSV || '../../question-bank-template.csv'),
    goldStandardCsv: resolve('../../question-bank-template.csv'),
    logDir: resolve(process.env.LOG_DIR || './logs'),
    tempDir: resolve('./temp'),
  },

  // Validation rules
  validation: {
    minSolutionLength: 50, // Reduced from 100 to allow shorter solutions
    verticalLevelRange: [0, 8] as const,
    horizontalLevelRange: [1, 8] as const, // Updated for 9×8 V×H matrix
    requiredFields: [
      'question_id',
      'source_book',
      'source_year',
      'class',
      'subject',
      'chapter',
      'topic',
      'skill',
      'question_type',
      'vertical_level',
      'horizontal_level',
      'cognitive_type',
      'question_text',
      'correct_answer',
      'solution',
    ] as const,
  },

  // Quality control
  quality: {
    humanReviewPercentage: 10, // 10% random sampling
    confidenceThreshold: 0.7, // Flag questions below this confidence
  },
} as const;

export type Config = typeof config;
