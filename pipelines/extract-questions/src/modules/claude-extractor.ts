/**
 * Claude Vision API Extractor
 * Uses Claude Sonnet 4.5 to extract questions from PDF page images
 * Supports 5 specialized templates for different source types
 */

import Anthropic from '@anthropic-ai/sdk';
import { randomUUID } from 'crypto';
import { config } from '../config/settings.js';
import { Question, QuestionSchema, ExtractionResult, getVHRange } from '../config/types.js';
import { Logger } from '../utils/logger.js';
import { PDFPage } from './pdf-converter.js';
import {
  SourceCategory,
  detectSourceCategory,
  getTemplateForSource,
  buildExtractionPrompt,
} from './prompt-templates.js';

export interface SourceInfo {
  category: SourceCategory;
  sourceType: 'foundational' | 'practice' | 'reference' | 'pyq' | 'competitive';
  verticalRange: { min: number; max: number };
  horizontalRange: { min: number; max: number };
}

export class ClaudeExtractor {
  private client: Anthropic;
  private logger: Logger;
  private fewShotPrompt: string;
  private templateCache: Map<SourceCategory, string>;
  private currentPdfPath: string = '';
  private currentSourceInfo: SourceInfo | null = null;

  constructor(logger: Logger, fewShotPrompt: string) {
    if (!config.anthropic.apiKey) {
      throw new Error('ANTHROPIC_API_KEY environment variable not set');
    }

    this.client = new Anthropic({
      apiKey: config.anthropic.apiKey,
    });

    this.logger = logger;
    this.fewShotPrompt = fewShotPrompt;
    this.templateCache = new Map();
  }

  /**
   * Detect source type from PDF path
   */
  detectSourceType(pdfPath: string): SourceInfo {
    const category = detectSourceCategory(pdfPath);

    // Determine source type and V×H range based on category
    let sourceType: SourceInfo['sourceType'];
    let verticalRange: { min: number; max: number };
    let horizontalRange: { min: number; max: number };

    switch (category) {
      case 'ncert':
        sourceType = 'foundational';
        // Check if it's Exemplar (slightly harder range)
        if (pdfPath.toLowerCase().includes('exemplar')) {
          verticalRange = { min: 1, max: 3 };
          horizontalRange = { min: 1, max: 3 };
        } else {
          verticalRange = { min: 0, max: 2 };
          horizontalRange = { min: 1, max: 2 };
        }
        break;

      case 'reference':
        sourceType = 'reference';
        // HC Verma has higher range
        if (pdfPath.toLowerCase().includes('verma')) {
          verticalRange = { min: 4, max: 6 };
        } else {
          verticalRange = { min: 3, max: 5 };
        }
        horizontalRange = { min: 5, max: 6 };
        break;

      case 'pyq':
        // Check if sample paper or actual PYQ
        if (pdfPath.toLowerCase().includes('sample')) {
          sourceType = 'practice';
          verticalRange = { min: 2, max: 4 };
          horizontalRange = { min: 3, max: 4 };
        } else {
          sourceType = 'pyq';
          verticalRange = { min: 4, max: 6 };
          horizontalRange = { min: 7, max: 8 };
        }
        break;

      case 'jee_neet':
        sourceType = 'competitive';
        verticalRange = { min: 7, max: 7 }; // V7 for JEE Main and NEET
        horizontalRange = { min: 7, max: 8 };
        break;

      case 'advanced':
        sourceType = 'competitive';
        verticalRange = { min: 8, max: 8 }; // V8 for JEE Advanced and Olympiad
        horizontalRange = { min: 7, max: 8 };
        break;
    }

    return {
      category,
      sourceType,
      verticalRange,
      horizontalRange,
    };
  }

  /**
   * Get or build template for a source category
   */
  private getTemplate(category: SourceCategory): string {
    if (!this.templateCache.has(category)) {
      const template = getTemplateForSource(category, this.fewShotPrompt);
      this.templateCache.set(category, template);
    }
    return this.templateCache.get(category)!;
  }

  /**
   * Set current PDF for extraction (call before extractFromPage)
   */
  setPdfContext(pdfPath: string): SourceInfo {
    this.currentPdfPath = pdfPath;
    this.currentSourceInfo = this.detectSourceType(pdfPath);

    this.logger.info(
      `Source detected: ${this.currentSourceInfo.category} | ` +
        `V${this.currentSourceInfo.verticalRange.min}-${this.currentSourceInfo.verticalRange.max}, ` +
        `H${this.currentSourceInfo.horizontalRange.min}-${this.currentSourceInfo.horizontalRange.max} | ` +
        `type: ${this.currentSourceInfo.sourceType}`
    );

    return this.currentSourceInfo;
  }

  /**
   * Get current source info
   */
  getSourceInfo(): SourceInfo | null {
    return this.currentSourceInfo;
  }

  /**
   * Extract questions from a PDF page image
   */
  async extractFromPage(page: PDFPage): Promise<ExtractionResult> {
    const startTime = Date.now();

    try {
      // Ensure PDF context is set (auto-detect if not)
      if (!this.currentSourceInfo || this.currentPdfPath !== page.pdfPath) {
        this.setPdfContext(page.pdfPath);
      }

      // Get appropriate template for this source
      const template = this.getTemplate(this.currentSourceInfo!.category);

      await this.logger.info(
        `Extracting from page ${page.pageNumber} of ${page.pdfPath} ` +
          `(template: ${this.currentSourceInfo!.category})`
      );

      const message = await this.client.messages.create({
        model: config.anthropic.model,
        max_tokens: config.anthropic.maxTokens,
        temperature: config.anthropic.temperature,
        messages: [
          {
            role: 'user',
            content: [
              {
                type: 'image',
                source: {
                  type: 'base64',
                  media_type: 'image/jpeg',
                  data: page.imageBase64,
                },
              },
              {
                type: 'text',
                text: template,
              },
            ],
          },
        ],
      });

      // Parse response
      const responseText =
        message.content[0].type === 'text' ? message.content[0].text : '';

      const questions = this.parseResponse(responseText);

      const processingTime = Date.now() - startTime;

      await this.logger.success(
        `Extracted ${questions.length} questions from page ${page.pageNumber} in ${processingTime}ms`
      );

      return {
        success: true,
        questions,
        errors: [],
        metadata: {
          pdfPath: page.pdfPath,
          pageNumber: page.pageNumber,
          processingTime,
          tokenUsage: {
            input: message.usage.input_tokens,
            output: message.usage.output_tokens,
          },
        },
      };
    } catch (error) {
      await this.logger.error(
        `Failed to extract from page ${page.pageNumber}`,
        error as Error
      );

      return {
        success: false,
        questions: [],
        errors: [(error as Error).message],
        metadata: {
          pdfPath: page.pdfPath,
          pageNumber: page.pageNumber,
          processingTime: Date.now() - startTime,
        },
      };
    }
  }

  /**
   * Calculate cost for API usage
   */
  calculateCost(inputTokens: number, outputTokens: number): number {
    // Pricing depends on model (check settings.ts):
    // - Sonnet 4.5: $3/1M input, $15/1M output
    // - Haiku 4.5: $1/1M input, $5/1M output
    const isHaiku = config.anthropic.model.includes('haiku');
    const inputRate = isHaiku ? 1.0 : 3.0;
    const outputRate = isHaiku ? 5.0 : 15.0;

    const inputCost = (inputTokens / 1_000_000) * inputRate;
    const outputCost = (outputTokens / 1_000_000) * outputRate;
    return inputCost + outputCost;
  }

  /**
   * Parse Claude's response and validate questions
   */
  private parseResponse(responseText: string): Question[] {
    try {
      // Extract JSON from markdown code blocks if present
      let jsonText = responseText;

      const codeBlockMatch = responseText.match(/```json\s*([\s\S]*?)\s*```/);
      if (codeBlockMatch) {
        jsonText = codeBlockMatch[1];
      }

      // Handle truncated JSON - try to recover valid questions
      let rawQuestions: any[];
      try {
        rawQuestions = JSON.parse(jsonText);
      } catch (parseError) {
        // Try to fix truncated JSON by finding last complete object
        this.logger.warn('JSON parse failed, attempting recovery...');
        const recovered = this.recoverTruncatedJson(jsonText);
        if (recovered.length === 0) {
          throw parseError;
        }
        rawQuestions = recovered;
        this.logger.info(`Recovered ${rawQuestions.length} questions from truncated JSON`);
      }

      if (!Array.isArray(rawQuestions)) {
        throw new Error('Response is not an array');
      }

      // Validate each question against schema
      const validQuestions: Question[] = [];

      for (const raw of rawQuestions) {
        try {
          // Auto-generate UUID if missing or invalid
          if (!raw.id || !this.isValidUUID(raw.id)) {
            raw.id = randomUUID();
          }

          // Ensure arrays are not stringified
          if (typeof raw.prerequisite_topics === 'string') {
            try {
              raw.prerequisite_topics = JSON.parse(raw.prerequisite_topics);
            } catch {
              raw.prerequisite_topics = [];
            }
          }
          if (typeof raw.tags === 'string') {
            try {
              raw.tags = JSON.parse(raw.tags);
            } catch {
              raw.tags = [];
            }
          }

          const validated = QuestionSchema.parse(raw);
          validQuestions.push(validated);
        } catch (validationError) {
          this.logger.warn(
            `Question validation failed: ${(validationError as Error).message}`
          );
          // Continue with other questions
        }
      }

      return validQuestions;
    } catch (error) {
      this.logger.error('Failed to parse Claude response', error as Error);
      return [];
    }
  }

  /**
   * Check if string is valid UUID
   */
  private isValidUUID(str: string): boolean {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(str);
  }

  /**
   * Attempt to recover questions from truncated JSON
   */
  private recoverTruncatedJson(jsonText: string): any[] {
    const questions: any[] = [];

    // Try to find complete question objects
    // Look for patterns like {"question_id": ... }
    const objectMatches = jsonText.matchAll(/\{[^{}]*"question_id"[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/g);

    for (const match of objectMatches) {
      try {
        const obj = JSON.parse(match[0]);
        if (obj.question_id && obj.question_text) {
          questions.push(obj);
        }
      } catch {
        // Skip malformed objects
      }
    }

    return questions;
  }
}
