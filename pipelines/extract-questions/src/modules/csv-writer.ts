/**
 * CSV Writer
 * Appends extracted questions to master CSV file with validation
 */

import { readFile, appendFile } from 'fs/promises';
import { stringify } from 'csv-stringify/sync';
import { config } from '../config/settings.js';
import { Question, getVHRange } from '../config/types.js';
import { Logger } from '../utils/logger.js';

export class CSVWriter {
  private logger: Logger;
  private outputPath: string;

  constructor(logger: Logger) {
    this.logger = logger;
    this.outputPath = config.paths.outputCsv;
  }

  /**
   * Append questions to CSV file
   */
  async appendQuestions(questions: Question[]): Promise<void> {
    if (questions.length === 0) {
      await this.logger.warn('No questions to append to CSV');
      return;
    }

    try {
      // Map Question fields directly (schema matches CSV columns)
      const processedQuestions = questions.map((q) => ({
        question_id: q.question_id,
        source_book: q.source_book || '',
        source_year: q.source_year || '',
        class: q.class || '',
        subject: q.subject || '',
        chapter: q.chapter || '',
        topic: q.topic || '',
        subtopic: q.subtopic || '',
        skill: q.skill || '',
        question_type: q.question_type || '',
        vertical_level: q.vertical_level ?? '',
        horizontal_level: q.horizontal_level ?? '',
        cognitive_type: q.cognitive_type || '',
        question_text: q.question_text || '',
        option_a: q.option_a || '',
        option_b: q.option_b || '',
        option_c: q.option_c || '',
        option_d: q.option_d || '',
        correct_answer: q.correct_answer || '',
        solution: q.solution || '',
        explanation: q.explanation || '',
        marks: q.marks || '',
        time_expected: q.time_expected || '',
        prerequisite_topics: JSON.stringify(q.prerequisite_topics || []),
        learning_outcome_id: q.learning_outcome_id || '',
        tags: JSON.stringify(q.tags || []),
        difficulty_rating: q.difficulty_rating || '',
        is_board_pattern: q.is_board_pattern ?? '',
        is_competitive: q.is_competitive ?? '',
        image_path: q.image_path || '',
        video_solution_url: q.video_solution_url || '',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        extraction_status: 'extracted',
        verified_by: '',
        notes: '',
      }));

      // Convert questions to CSV rows
      const csvData = stringify(processedQuestions, {
        header: false, // Don't add header, file already has it
        columns: this.getColumnOrder(),
      });

      // Append to file
      await appendFile(this.outputPath, csvData);

      await this.logger.success(
        `Appended ${questions.length} questions to ${this.outputPath}`
      );
    } catch (error) {
      await this.logger.error('Failed to write to CSV', error as Error);
      throw error;
    }
  }

  /**
   * Get the column order matching the gold standard CSV template
   */
  private getColumnOrder(): string[] {
    // Must match exactly: question-bank-template.csv header
    return [
      'question_id',
      'source_book',
      'source_year',
      'class',
      'subject',
      'chapter',
      'topic',
      'subtopic',
      'skill',
      'question_type',
      'vertical_level',
      'horizontal_level',
      'cognitive_type',
      'question_text',
      'option_a',
      'option_b',
      'option_c',
      'option_d',
      'correct_answer',
      'solution',
      'explanation',
      'marks',
      'time_expected',
      'prerequisite_topics',
      'learning_outcome_id',
      'tags',
      'difficulty_rating',
      'is_board_pattern',
      'is_competitive',
      'image_path',
      'video_solution_url',
      'created_at',
      'updated_at',
      'extraction_status',
      'verified_by',
      'notes',
    ];
  }

  /**
   * Validate question before writing
   */
  validateQuestion(question: Question): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    // Check required fields
    if (!question.question_id) errors.push('Missing question_id');
    if (!question.solution || question.solution.length < config.validation.minSolutionLength) {
      errors.push(`Solution too short (min ${config.validation.minSolutionLength} chars)`);
    }

    // Validate V×H levels are within valid range
    if (question.vertical_level < 0 || question.vertical_level > 8) {
      errors.push('vertical_level must be 0-8');
    }
    if (question.horizontal_level < 1 || question.horizontal_level > 8) {
      errors.push('horizontal_level must be 1-8');
    }

    // Validate V×H matches source type
    if (question.source_book) {
      const vhRange = getVHRange(question.source_book);
      if (
        question.vertical_level < vhRange.vertical.min ||
        question.vertical_level > vhRange.vertical.max
      ) {
        errors.push(
          `vertical_level ${question.vertical_level} outside valid range for ${question.source_book} (${vhRange.vertical.min}-${vhRange.vertical.max})`
        );
      }
      if (
        question.horizontal_level < vhRange.horizontal.min ||
        question.horizontal_level > vhRange.horizontal.max
      ) {
        errors.push(
          `horizontal_level ${question.horizontal_level} outside valid range for ${question.source_book} (${vhRange.horizontal.min}-${vhRange.horizontal.max})`
        );
      }
    }

    // Validate MCQ consistency
    if (question.question_type === 'MCQ_SINGLE' || question.question_type === 'MCQ_MULTI' || question.question_type === 'MCQ') {
      if (!question.option_a || !question.option_b) {
        errors.push('MCQ questions need at least options A and B');
      }
      if (!question.correct_answer) {
        errors.push('MCQ questions need correct_answer');
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Get statistics about extracted questions
   */
  async getStats(): Promise<{
    totalQuestions: number;
    bySource: Record<string, number>;
    bySubject: Record<string, number>;
  }> {
    try {
      const csvContent = await readFile(this.outputPath, 'utf-8');
      const lines = csvContent.trim().split('\n');
      const totalQuestions = lines.length - 1; // Subtract header

      // Parse to get distribution (simplified)
      const bySource: Record<string, number> = {};
      const bySubject: Record<string, number> = {};

      // Count by looking at question IDs
      for (const line of lines.slice(1)) {
        const match = line.match(/^Q_([^_]+)_/);
        if (match) {
          const source = match[1];
          bySource[source] = (bySource[source] || 0) + 1;
        }
      }

      return { totalQuestions, bySource, bySubject };
    } catch (error) {
      return { totalQuestions: 0, bySource: {}, bySubject: {} };
    }
  }
}
