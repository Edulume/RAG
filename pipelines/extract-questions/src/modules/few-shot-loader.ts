/**
 * Few-Shot Example Loader
 * Loads gold-standard questions from CSV to use as examples
 */

import { readFile } from 'fs/promises';
import { parse } from 'csv-parse/sync';
import { config } from '../config/settings.js';
import { Question, FewShotExample, getVHRange } from '../config/types.js';
import { Logger } from '../utils/logger.js';

export class FewShotLoader {
  private logger: Logger;
  private examples: FewShotExample[] = [];

  constructor(logger: Logger) {
    this.logger = logger;
  }

  /**
   * Load gold-standard questions from CSV
   */
  async loadExamples(): Promise<void> {
    try {
      const csvContent = await readFile(config.paths.goldStandardCsv, 'utf-8');

      const records = parse(csvContent, {
        columns: true,
        skip_empty_lines: true,
        relax_column_count: true,
        quote: '"',
        escape: '"',
        cast: (value, context) => {
          // Convert numeric fields
          if (
            context.column === 'source_year' ||
            context.column === 'class' ||
            context.column === 'difficulty_rating' ||
            context.column === 'vertical_level' ||
            context.column === 'horizontal_level' ||
            context.column === 'marks' ||
            context.column === 'time_expected'
          ) {
            return value ? parseInt(value) : undefined;
          }

          // Convert boolean fields
          if (
            context.column === 'is_board_pattern' ||
            context.column === 'is_competitive'
          ) {
            return value === 'TRUE' || value === 'true';
          }

          // Parse JSON array fields
          if (
            context.column === 'prerequisite_topics' ||
            context.column === 'tags'
          ) {
            try {
              return value ? JSON.parse(value) : [];
            } catch {
              return [];
            }
          }

          return value;
        },
      });

      await this.logger.info(`Loaded ${records.length} gold-standard questions`);

      // Map CSV columns to Question type (both use same names now)
      const mappedRecords = records.map((r: any) => {
        const sourceBook = r.source_book || 'NCERT Exemplar';
        const vhRange = getVHRange(sourceBook);
        const difficultyRating = r.difficulty_rating || 3;

        let verticalLevel = r.vertical_level;
        let horizontalLevel = r.horizontal_level;

        // Auto-assign if not present
        if (verticalLevel === undefined) {
          const vRange = vhRange.vertical.max - vhRange.vertical.min;
          const difficultyRatio = Math.min((difficultyRating - 1) / 9, 1);
          verticalLevel = Math.round(vhRange.vertical.min + difficultyRatio * vRange);
        }

        if (horizontalLevel === undefined) {
          horizontalLevel = Math.round(
            (vhRange.horizontal.min + vhRange.horizontal.max) / 2
          );
        }

        return {
          question_id: r.question_id,
          source_book: sourceBook,
          source_year: r.source_year || 2024,
          class: r.class,
          subject: r.subject,
          chapter: r.chapter,
          topic: r.topic,
          subtopic: r.subtopic || '',
          skill: r.skill || '',
          question_type: r.question_type,
          vertical_level: verticalLevel,
          horizontal_level: horizontalLevel,
          cognitive_type: r.cognitive_type || 'Apply',
          question_text: r.question_text,
          option_a: r.option_a || '',
          option_b: r.option_b || '',
          option_c: r.option_c || '',
          option_d: r.option_d || '',
          correct_answer: r.correct_answer || '',
          solution: r.solution || '',
          explanation: r.explanation || '',
          marks: r.marks,
          time_expected: r.time_expected || 120,
          prerequisite_topics: r.prerequisite_topics || [],
          learning_outcome_id: r.learning_outcome_id || '',
          tags: r.tags || [],
          difficulty_rating: difficultyRating,
          is_board_pattern: r.is_board_pattern,
          is_competitive: r.is_competitive,
          image_path: r.image_path || '',
          video_solution_url: r.video_solution_url || '',
          created_at: r.created_at || '',
          updated_at: r.updated_at || '',
          extraction_status: r.extraction_status || 'pending',
          verified_by: r.verified_by || '',
          notes: r.notes || '',
        } as Question;
      });

      // Convert to FewShotExample format with diversity
      this.examples = this.selectDiverseExamples(mappedRecords);

      await this.logger.success(
        `Selected ${this.examples.length} diverse few-shot examples`
      );
    } catch (error) {
      await this.logger.error('Failed to load few-shot examples', error as Error);
      throw error;
    }
  }

  /**
   * Select diverse examples covering different question types, subjects, sources
   */
  private selectDiverseExamples(records: Question[]): FewShotExample[] {
    const examples: FewShotExample[] = [];
    const questionTypes = ['MCQ_SINGLE', 'MCQ_MULTI', 'MCQ', 'SHORT_ANSWER', 'LONG_ANSWER', 'NUMERICAL'];

    // Pick 1-2 examples from each question type
    for (const type of questionTypes) {
      const matches = records.filter((r) => r.question_type === type).slice(0, 2);
      matches.forEach((record) => {
        examples.push({
          question: record,
          context: `Example ${type} question`,
        });
      });
    }

    // Ensure we have competitive exam examples
    const jeeExamples = records
      .filter((r) => r.source_book && r.source_book.includes('JEE'))
      .slice(0, 2);
    const neetExamples = records
      .filter((r) => r.source_book && r.source_book.includes('NEET'))
      .slice(0, 2);

    jeeExamples.forEach((record) => {
      examples.push({
        question: record,
        context: 'JEE competitive level example',
      });
    });

    neetExamples.forEach((record) => {
      examples.push({
        question: record,
        context: 'NEET competitive level example',
      });
    });

    return examples.slice(0, 12);
  }

  /**
   * Get formatted examples for prompt
   */
  getExamplesForPrompt(): string {
    return this.examples
      .map((example, idx) => {
        const q = example.question;

        // Build example JSON matching schema (field names match CSV)
        const exampleJson: any = {
          question_id: q.question_id,
          source_book: q.source_book,
          source_year: q.source_year,
          vertical_level: q.vertical_level,
          horizontal_level: q.horizontal_level,
          class: q.class,
          subject: q.subject,
          chapter: q.chapter,
          topic: q.topic,
          subtopic: q.subtopic || '',
          skill: q.skill || '',
          question_type: q.question_type,
          cognitive_type: q.cognitive_type,
          question_text: q.question_text.substring(0, 100) + '...',
          option_a: q.option_a || '',
          option_b: q.option_b || '',
          option_c: q.option_c || '',
          option_d: q.option_d || '',
          correct_answer: q.correct_answer,
          solution: q.solution.substring(0, 200) + '...',
          explanation: q.explanation || '',
          marks: q.marks,
          time_expected: q.time_expected,
          prerequisite_topics: q.prerequisite_topics || [],
          learning_outcome_id: q.learning_outcome_id || '',
          tags: q.tags || [],
          difficulty_rating: q.difficulty_rating,
          is_board_pattern: q.is_board_pattern,
          is_competitive: q.is_competitive,
          image_path: '',
          video_solution_url: '',
          extraction_status: 'extracted',
          verified_by: '',
          notes: '',
        };

        return `
### Example ${idx + 1}: ${example.context}
V×H: V${q.vertical_level}, H${q.horizontal_level}

${JSON.stringify(exampleJson, null, 2)}
`;
      })
      .join('\n\n');
  }

  getExamples(): FewShotExample[] {
    return this.examples;
  }
}
