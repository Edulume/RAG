#!/usr/bin/env bun

/**
 * Validation Script for Extracted Questions
 * Samples questions and validates V×H assignments, schema compliance
 */

import { readFile } from 'fs/promises';
import { parse } from 'csv-parse/sync';
import { config } from './config/settings.js';
import { getVHRange, VH_RANGES } from './config/types.js';

interface ValidationError {
  questionId: string;
  field: string;
  error: string;
  value: any;
}

interface ValidationResult {
  totalQuestions: number;
  sampleSize: number;
  validQuestions: number;
  invalidQuestions: number;
  errors: ValidationError[];
  byCategory: Record<string, { valid: number; invalid: number; errors: string[] }>;
}

const SAMPLE_RATE = 0.1; // 10% sample

/**
 * Derive source_type from question_id pattern
 */
function deriveSourceType(q: any): string {
  const qid = q.question_id || '';
  const source = q.source_book || '';

  if (qid.startsWith('Q_NCERT') || source.includes('NCERT')) return 'foundational';
  if (qid.startsWith('Q_CBSE') || source.includes('CBSE')) return 'pyq';
  if (qid.startsWith('Q_JEE') || source.includes('JEE')) return 'competitive';
  if (qid.startsWith('Q_NEET') || source.includes('NEET')) return 'competitive';
  if (source.includes('Pradeep') || source.includes('Oswaal')) return 'reference';
  return 'foundational'; // default
}

async function validateExtraction(): Promise<void> {
  console.log('='.repeat(60));
  console.log('Question Bank Validation');
  console.log('='.repeat(60));

  try {
    // Load extracted questions
    const csvPath = config.paths.outputCsv;
    console.log(`\nLoading questions from: ${csvPath}`);

    const csvContent = await readFile(csvPath, 'utf-8');
    const questions = parse(csvContent, {
      columns: true,
      skip_empty_lines: true,
      relax_column_count: true,
    });

    const totalQuestions = questions.length;
    console.log(`Total questions: ${totalQuestions}`);

    // Sample questions
    const sampleSize = Math.max(1, Math.floor(totalQuestions * SAMPLE_RATE));
    const sampledQuestions = sampleQuestions(questions, sampleSize);
    console.log(`Sample size (10%): ${sampleSize}`);

    // Validate each question
    const result: ValidationResult = {
      totalQuestions,
      sampleSize,
      validQuestions: 0,
      invalidQuestions: 0,
      errors: [],
      byCategory: {},
    };

    for (const q of sampledQuestions) {
      const errors = validateQuestion(q);

      if (errors.length === 0) {
        result.validQuestions++;
      } else {
        result.invalidQuestions++;
        result.errors.push(...errors);
      }

      // Track by source type (derived from question_id)
      const sourceType = deriveSourceType(q);
      if (!result.byCategory[sourceType]) {
        result.byCategory[sourceType] = { valid: 0, invalid: 0, errors: [] };
      }
      if (errors.length === 0) {
        result.byCategory[sourceType].valid++;
      } else {
        result.byCategory[sourceType].invalid++;
        result.byCategory[sourceType].errors.push(
          ...errors.map(e => `${e.questionId}: ${e.error}`)
        );
      }
    }

    // Print report
    printReport(result);

  } catch (error) {
    console.error('Validation failed:', (error as Error).message);
    process.exit(1);
  }
}

function sampleQuestions(questions: any[], sampleSize: number): any[] {
  // Stratified sampling by source_type
  const byType: Record<string, any[]> = {};

  for (const q of questions) {
    const type = q.source_type || 'unknown';
    if (!byType[type]) byType[type] = [];
    byType[type].push(q);
  }

  const sampled: any[] = [];
  const typeSampleSize = Math.ceil(sampleSize / Object.keys(byType).length);

  for (const [type, typeQuestions] of Object.entries(byType)) {
    // Random sample from this type
    const shuffled = typeQuestions.sort(() => Math.random() - 0.5);
    sampled.push(...shuffled.slice(0, typeSampleSize));
  }

  return sampled.slice(0, sampleSize);
}

function validateQuestion(q: any): ValidationError[] {
  const errors: ValidationError[] = [];
  const questionId = q.question_id || 'unknown';

  // 1. Check V×H fields exist
  if (q.vertical_level === undefined || q.vertical_level === '') {
    errors.push({
      questionId,
      field: 'vertical_level',
      error: 'Missing vertical_level',
      value: q.vertical_level,
    });
  }

  if (q.horizontal_level === undefined || q.horizontal_level === '') {
    errors.push({
      questionId,
      field: 'horizontal_level',
      error: 'Missing horizontal_level',
      value: q.horizontal_level,
    });
  }

  // 2. Validate V×H range (derived from source_book)
  const sourceBook = q.source_book || '';
  if (sourceBook && q.vertical_level !== undefined && q.horizontal_level !== undefined) {
    const vhRange = getVHRange(sourceBook);
    const vLevel = parseInt(q.vertical_level);
    const hLevel = parseInt(q.horizontal_level);

    if (!isNaN(vLevel) && (vLevel < vhRange.vertical.min || vLevel > vhRange.vertical.max)) {
      errors.push({
        questionId,
        field: 'vertical_level',
        error: `V${vLevel} outside valid range V${vhRange.vertical.min}-${vhRange.vertical.max} for ${sourceBook}`,
        value: vLevel,
      });
    }

    if (!isNaN(hLevel) && (hLevel < vhRange.horizontal.min || hLevel > vhRange.horizontal.max)) {
      errors.push({
        questionId,
        field: 'horizontal_level',
        error: `H${hLevel} outside valid range H${vhRange.horizontal.min}-${vhRange.horizontal.max} for ${sourceBook}`,
        value: hLevel,
      });
    }
  }

  // 3. Check JSON arrays are not stringified strings
  if (q.prerequisite_topics) {
    const prereqs = q.prerequisite_topics;
    if (typeof prereqs === 'string') {
      // It's already a string in CSV, check if it looks like a double-stringified JSON
      if (prereqs.startsWith('"[') || prereqs.includes('\\"')) {
        errors.push({
          questionId,
          field: 'prerequisite_topics',
          error: 'Double-stringified JSON array detected',
          value: prereqs.substring(0, 50),
        });
      }
    }
  }

  if (q.tags) {
    const tags = q.tags;
    if (typeof tags === 'string') {
      if (tags.startsWith('"[') || tags.includes('\\"')) {
        errors.push({
          questionId,
          field: 'tags',
          error: 'Double-stringified JSON array detected',
          value: tags.substring(0, 50),
        });
      }
    }
  }

  // 4. Check solution length > 50 chars
  if (!q.solution || q.solution.length < 50) {
    errors.push({
      questionId,
      field: 'solution',
      error: `Solution too short (${q.solution?.length || 0} chars, min 50)`,
      value: q.solution?.substring(0, 50),
    });
  }

  // 5. MCQ validation
  if (q.question_type === 'MCQ_SINGLE' || q.question_type === 'MCQ_MULTI' || q.question_type === 'MCQ') {
    if (!q.correct_answer) {
      errors.push({
        questionId,
        field: 'correct_answer',
        error: 'MCQ missing correct_answer',
        value: q.correct_answer,
      });
    }

    if (!q.option_a || !q.option_b) {
      errors.push({
        questionId,
        field: 'options',
        error: 'MCQ missing option_a or option_b',
        value: `A: ${q.option_a?.substring(0, 20)}, B: ${q.option_b?.substring(0, 20)}`,
      });
    }
  }

  // 6. Check required fields
  if (!q.question_text || q.question_text.length < 10) {
    errors.push({
      questionId,
      field: 'question_text',
      error: 'Question text too short or missing',
      value: q.question_text?.substring(0, 30),
    });
  }

  if (!q.subject) {
    errors.push({
      questionId,
      field: 'subject',
      error: 'Missing subject',
      value: q.subject,
    });
  }

  if (!q.chapter) {
    errors.push({
      questionId,
      field: 'chapter',
      error: 'Missing chapter',
      value: q.chapter,
    });
  }

  if (!q.topic) {
    errors.push({
      questionId,
      field: 'topic',
      error: 'Missing topic',
      value: q.topic,
    });
  }

  return errors;
}

function printReport(result: ValidationResult): void {
  console.log('\n' + '='.repeat(60));
  console.log('VALIDATION REPORT');
  console.log('='.repeat(60));

  const validRate = ((result.validQuestions / result.sampleSize) * 100).toFixed(1);
  const errorRate = ((result.invalidQuestions / result.sampleSize) * 100).toFixed(1);

  console.log(`\n📊 SUMMARY`);
  console.log(`   Total questions:  ${result.totalQuestions}`);
  console.log(`   Sample size:      ${result.sampleSize} (10%)`);
  console.log(`   Valid:            ${result.validQuestions} (${validRate}%)`);
  console.log(`   Invalid:          ${result.invalidQuestions} (${errorRate}%)`);

  // Check if error rate is acceptable
  if (parseFloat(errorRate) <= 2) {
    console.log(`\n✅ Error rate ${errorRate}% is within acceptable threshold (2%)`);
  } else {
    console.log(`\n❌ Error rate ${errorRate}% EXCEEDS acceptable threshold (2%)`);
  }

  // By category breakdown
  console.log(`\n📁 BY SOURCE TYPE`);
  for (const [type, stats] of Object.entries(result.byCategory)) {
    const total = stats.valid + stats.invalid;
    const typeValidRate = ((stats.valid / total) * 100).toFixed(1);
    console.log(`   ${type.padEnd(15)}: ${stats.valid}/${total} valid (${typeValidRate}%)`);
  }

  // Error breakdown
  if (result.errors.length > 0) {
    console.log(`\n⚠️  ERROR BREAKDOWN`);

    // Group errors by field
    const byField: Record<string, number> = {};
    for (const err of result.errors) {
      byField[err.field] = (byField[err.field] || 0) + 1;
    }

    for (const [field, count] of Object.entries(byField).sort((a, b) => b[1] - a[1])) {
      console.log(`   ${field.padEnd(20)}: ${count} errors`);
    }

    // Show sample errors
    console.log(`\n📝 SAMPLE ERRORS (first 10)`);
    for (const err of result.errors.slice(0, 10)) {
      console.log(`   [${err.questionId}] ${err.field}: ${err.error}`);
    }
  }

  console.log('\n' + '='.repeat(60));
}

// Run if called directly
if (import.meta.main) {
  validateExtraction();
}
