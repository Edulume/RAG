/**
 * Extraction Tracker
 * Tracks extraction progress, costs, and enables resume from failures
 */

import { readFile, appendFile, writeFile } from 'fs/promises';
import { existsSync } from 'fs';
import { parse } from 'csv-parse/sync';
import { stringify } from 'csv-stringify/sync';
import { Logger } from '../utils/logger.js';

export interface ExtractionLog {
  pdf_path: string;
  source_type: string;
  vertical_range: string; // "0-2"
  horizontal_range: string; // "1-3"
  questions_extracted: number;
  pages_processed: number;
  status: 'success' | 'failed' | 'partial';
  error_message: string;
  cost_usd: number;
  started_at: string;
  completed_at: string;
}

export interface ProgressSummary {
  total: number;
  completed: number;
  failed: number;
  partial: number;
  remaining: number;
}

export interface CostSummary {
  total: number;
  bySourceType: Record<string, number>;
  avgPerQuestion: number;
  totalQuestions: number;
}

export class ExtractionTracker {
  private logPath: string;
  private logger: Logger;
  private cache: Map<string, ExtractionLog>;
  private initialized: boolean = false;

  constructor(logPath: string, logger: Logger) {
    this.logPath = logPath;
    this.logger = logger;
    this.cache = new Map();
  }

  /**
   * Initialize tracker, loading existing log file if present
   */
  async init(): Promise<void> {
    if (this.initialized) return;

    try {
      if (existsSync(this.logPath)) {
        const content = await readFile(this.logPath, 'utf-8');
        const records = parse(content, {
          columns: true,
          skip_empty_lines: true,
        }) as ExtractionLog[];

        for (const record of records) {
          // Normalize path for consistent lookup
          const normalizedPath = this.normalizePath(record.pdf_path);
          this.cache.set(normalizedPath, {
            ...record,
            questions_extracted: Number(record.questions_extracted),
            pages_processed: Number(record.pages_processed),
            cost_usd: Number(record.cost_usd),
          });
        }

        await this.logger.info(
          `Loaded ${this.cache.size} existing extraction records from ${this.logPath}`
        );
      } else {
        // Create new log file with header
        await this.createLogFile();
        await this.logger.info(`Created new extraction log at ${this.logPath}`);
      }

      this.initialized = true;
    } catch (error) {
      await this.logger.error('Failed to initialize extraction tracker', error as Error);
      throw error;
    }
  }

  /**
   * Create new log file with header
   */
  private async createLogFile(): Promise<void> {
    const header = stringify([], {
      header: true,
      columns: [
        'pdf_path',
        'source_type',
        'vertical_range',
        'horizontal_range',
        'questions_extracted',
        'pages_processed',
        'status',
        'error_message',
        'cost_usd',
        'started_at',
        'completed_at',
      ],
    });
    await writeFile(this.logPath, header);
  }

  /**
   * Normalize path for consistent comparison
   */
  private normalizePath(pdfPath: string): string {
    // Remove leading/trailing slashes and normalize
    return pdfPath.replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');
  }

  /**
   * Check if a PDF has already been successfully processed
   */
  isProcessed(pdfPath: string): boolean {
    const normalizedPath = this.normalizePath(pdfPath);
    const record = this.cache.get(normalizedPath);
    return record?.status === 'success';
  }

  /**
   * Check if a PDF has been attempted (even if failed)
   */
  wasAttempted(pdfPath: string): boolean {
    const normalizedPath = this.normalizePath(pdfPath);
    return this.cache.has(normalizedPath);
  }

  /**
   * Get the existing record for a PDF
   */
  getRecord(pdfPath: string): ExtractionLog | undefined {
    const normalizedPath = this.normalizePath(pdfPath);
    return this.cache.get(normalizedPath);
  }

  /**
   * Log a new extraction result
   */
  async logExtraction(log: ExtractionLog): Promise<void> {
    const normalizedPath = this.normalizePath(log.pdf_path);

    // Update cache
    this.cache.set(normalizedPath, log);

    // Append to CSV
    const csvRow = stringify([log], {
      header: false,
      columns: [
        'pdf_path',
        'source_type',
        'vertical_range',
        'horizontal_range',
        'questions_extracted',
        'pages_processed',
        'status',
        'error_message',
        'cost_usd',
        'started_at',
        'completed_at',
      ],
    });

    await appendFile(this.logPath, csvRow);

    await this.logger.info(
      `Logged extraction: ${log.pdf_path} - ${log.status} (${log.questions_extracted} questions, $${log.cost_usd.toFixed(4)})`
    );
  }

  /**
   * Get overall progress summary
   */
  getProgress(totalExpected?: number): ProgressSummary {
    let completed = 0;
    let failed = 0;
    let partial = 0;

    for (const record of this.cache.values()) {
      switch (record.status) {
        case 'success':
          completed++;
          break;
        case 'failed':
          failed++;
          break;
        case 'partial':
          partial++;
          break;
      }
    }

    const total = totalExpected || this.cache.size;
    const remaining = Math.max(0, total - completed - failed - partial);

    return {
      total,
      completed,
      failed,
      partial,
      remaining,
    };
  }

  /**
   * Get cost summary
   */
  getCostSummary(): CostSummary {
    let total = 0;
    let totalQuestions = 0;
    const bySourceType: Record<string, number> = {};

    for (const record of this.cache.values()) {
      total += record.cost_usd;
      totalQuestions += record.questions_extracted;

      if (!bySourceType[record.source_type]) {
        bySourceType[record.source_type] = 0;
      }
      bySourceType[record.source_type] += record.cost_usd;
    }

    return {
      total,
      bySourceType,
      avgPerQuestion: totalQuestions > 0 ? total / totalQuestions : 0,
      totalQuestions,
    };
  }

  /**
   * Get error rate
   */
  getErrorRate(): number {
    const progress = this.getProgress();
    const attempted = progress.completed + progress.failed + progress.partial;
    if (attempted === 0) return 0;
    return ((progress.failed + progress.partial) / attempted) * 100;
  }

  /**
   * Get all failed PDFs for retry
   */
  getFailedPDFs(): string[] {
    const failed: string[] = [];
    for (const [path, record] of this.cache.entries()) {
      if (record.status === 'failed' || record.status === 'partial') {
        failed.push(path);
      }
    }
    return failed;
  }

  /**
   * Filter a list of PDFs to only those not yet successfully processed
   */
  filterUnprocessed(pdfPaths: string[]): string[] {
    return pdfPaths.filter(path => !this.isProcessed(path));
  }

  /**
   * Generate a summary report
   */
  async generateReport(): Promise<string> {
    const progress = this.getProgress();
    const cost = this.getCostSummary();
    const errorRate = this.getErrorRate();

    const report = `
╔════════════════════════════════════════════════════════════════╗
║                    EXTRACTION PROGRESS REPORT                   ║
╠════════════════════════════════════════════════════════════════╣
║  PROGRESS                                                       ║
║  ─────────────────────────────────────────────────────────────  ║
║  Completed:  ${String(progress.completed).padStart(5)}  │  Failed:   ${String(progress.failed).padStart(5)}       ║
║  Partial:    ${String(progress.partial).padStart(5)}  │  Remaining: ${String(progress.remaining).padStart(5)}      ║
║  Total:      ${String(progress.total).padStart(5)}  │  Error Rate: ${errorRate.toFixed(1).padStart(5)}%      ║
╠════════════════════════════════════════════════════════════════╣
║  COST SUMMARY                                                   ║
║  ─────────────────────────────────────────────────────────────  ║
║  Total Cost:      $${cost.total.toFixed(2).padStart(8)}                                ║
║  Total Questions: ${String(cost.totalQuestions).padStart(9)}                                ║
║  Avg per Question: $${cost.avgPerQuestion.toFixed(4).padStart(7)}                               ║
╠════════════════════════════════════════════════════════════════╣
║  COST BY SOURCE TYPE                                            ║
║  ─────────────────────────────────────────────────────────────  ║
${Object.entries(cost.bySourceType)
  .map(([type, c]) => `║  ${type.padEnd(15)}: $${c.toFixed(2).padStart(8)}                              ║`)
  .join('\n')}
╚════════════════════════════════════════════════════════════════╝
`;

    return report;
  }

  /**
   * Check if error rate exceeds threshold
   */
  isErrorRateExceeded(threshold: number = 2): boolean {
    const errorRate = this.getErrorRate();
    return errorRate > threshold;
  }
}
