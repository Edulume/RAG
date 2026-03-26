#!/usr/bin/env bun

/**
 * Main Extraction Script
 * Orchestrates the entire question extraction pipeline with tracking
 */

import { glob } from 'glob';
import path from 'path';
import { Logger } from './utils/logger.js';
import { PDFConverter } from './modules/pdf-converter.js';
import { FewShotLoader } from './modules/few-shot-loader.js';
import { ClaudeExtractor } from './modules/claude-extractor.js';
import { CSVWriter } from './modules/csv-writer.js';
import { ExtractionTracker, ExtractionLog } from './modules/extraction-tracker.js';
import { config } from './config/settings.js';

interface ExtractionStats {
  totalPDFs: number;
  processedPDFs: number;
  skippedPDFs: number;
  totalPages: number;
  totalQuestions: number;
  totalCost: number;
  totalTime: number;
  successfulPages: number;
  failedPages: number;
}

// Error rate threshold (default 2%)
const ERROR_RATE_THRESHOLD = parseFloat(process.env.ERROR_RATE_THRESHOLD || '2');

async function main() {
  // Generate session ID
  const sessionId = Date.now().toString();
  const logger = new Logger(sessionId);

  await logger.info('='.repeat(60));
  await logger.info('Question Bank Automation - V×H Extraction System');
  await logger.info('='.repeat(60));

  const stats: ExtractionStats = {
    totalPDFs: 0,
    processedPDFs: 0,
    skippedPDFs: 0,
    totalPages: 0,
    totalQuestions: 0,
    totalCost: 0,
    totalTime: 0,
    successfulPages: 0,
    failedPages: 0,
  };

  try {
    // Step 1: Initialize extraction tracker
    await logger.info('Step 1: Initializing extraction tracker...');
    const trackerPath = path.join(config.paths.ragDir, 'extraction-log.csv');
    const tracker = new ExtractionTracker(trackerPath, logger);
    await tracker.init();

    // Show existing progress
    const existingProgress = tracker.getProgress();
    if (existingProgress.completed > 0) {
      await logger.info(
        `Resuming from previous session: ${existingProgress.completed} PDFs already processed`
      );
    }

    // Step 2: Load few-shot examples
    await logger.info('Step 2: Loading few-shot examples...');
    const fewShotLoader = new FewShotLoader(logger);
    await fewShotLoader.loadExamples();
    const fewShotPrompt = fewShotLoader.getExamplesForPrompt();

    // Step 3: Initialize modules
    await logger.info('Step 3: Initializing extraction modules...');
    const pdfConverter = new PDFConverter(logger);
    const claudeExtractor = new ClaudeExtractor(logger, fewShotPrompt);
    const csvWriter = new CSVWriter(logger);

    // Step 4: Find PDFs to process
    const pdfPattern = process.argv[2] || '**/Chapter-*.pdf';
    await logger.info(`Step 4: Finding PDFs matching: ${pdfPattern}`);

    const allPdfFiles = await glob(pdfPattern, {
      cwd: config.paths.inputPdfDir,
      absolute: true,
    });

    stats.totalPDFs = allPdfFiles.length;

    // Filter out already processed PDFs
    const pdfFiles = tracker.filterUnprocessed(allPdfFiles);
    stats.skippedPDFs = stats.totalPDFs - pdfFiles.length;

    await logger.info(`Found ${stats.totalPDFs} PDFs total`);
    await logger.info(`Skipping ${stats.skippedPDFs} already processed`);
    await logger.info(`Processing ${pdfFiles.length} remaining PDFs`);

    if (pdfFiles.length === 0) {
      await logger.success('All PDFs already processed!');
      const report = await tracker.generateReport();
      console.log(report);
      return;
    }

    // Step 5: Process each PDF
    for (let i = 0; i < pdfFiles.length; i++) {
      const pdfPath = pdfFiles[i];
      const pdfName = path.basename(pdfPath);
      const globalIndex = stats.skippedPDFs + i + 1;

      // Check error rate before continuing
      if (tracker.isErrorRateExceeded(ERROR_RATE_THRESHOLD)) {
        await logger.error(
          `Error rate exceeded ${ERROR_RATE_THRESHOLD}%. Stopping extraction.`
        );
        await logger.info('Review failed PDFs and fix issues before continuing.');
        break;
      }

      // Show progress with source info
      const sourceInfo = claudeExtractor.detectSourceType(pdfPath);
      await logger.info(
        `\n[${globalIndex}/${stats.totalPDFs}] ${pdfName}`
      );
      await logger.info(
        `Template: ${sourceInfo.category} | V${sourceInfo.verticalRange.min}-${sourceInfo.verticalRange.max}, H${sourceInfo.horizontalRange.min}-${sourceInfo.horizontalRange.max}`
      );

      const pdfStartTime = new Date().toISOString();
      const pdfStartMs = Date.now();
      let pdfQuestions = 0;
      let pdfCost = 0;
      let pdfStatus: 'success' | 'failed' | 'partial' = 'success';
      let errorMessage = '';

      try {
        // Set PDF context for template selection
        claudeExtractor.setPdfContext(pdfPath);

        // Convert PDF pages to images
        const pages = await pdfConverter.convertAllPages(pdfPath);
        stats.totalPages += pages.length;

        let pageErrors = 0;

        // Process each page
        for (const page of pages) {
          const result = await claudeExtractor.extractFromPage(page);

          if (result.success) {
            stats.successfulPages++;
            stats.totalQuestions += result.questions.length;
            pdfQuestions += result.questions.length;

            // Track API costs
            if (result.metadata.tokenUsage) {
              const cost = claudeExtractor.calculateCost(
                result.metadata.tokenUsage.input,
                result.metadata.tokenUsage.output
              );
              stats.totalCost += cost;
              pdfCost += cost;
            }

            // Write to CSV
            if (result.questions.length > 0) {
              await csvWriter.appendQuestions(result.questions);
            }
          } else {
            stats.failedPages++;
            pageErrors++;
            errorMessage = result.errors.join('; ');
            await logger.error(
              `Failed page ${page.pageNumber}: ${errorMessage}`
            );
          }
        }

        // Determine PDF status
        if (pageErrors === pages.length) {
          pdfStatus = 'failed';
        } else if (pageErrors > 0) {
          pdfStatus = 'partial';
        }

        // Clean up page images
        await pdfConverter.cleanup();

        stats.processedPDFs++;

      } catch (error) {
        pdfStatus = 'failed';
        errorMessage = (error as Error).message;
        await logger.error(`Failed to process PDF: ${pdfPath}`, error as Error);
      }

      const pdfEndTime = new Date().toISOString();
      const pdfTime = Date.now() - pdfStartMs;
      stats.totalTime += pdfTime;

      // Log extraction to tracker
      const extractionLog: ExtractionLog = {
        pdf_path: pdfPath,
        source_type: sourceInfo.sourceType,
        vertical_range: `${sourceInfo.verticalRange.min}-${sourceInfo.verticalRange.max}`,
        horizontal_range: `${sourceInfo.horizontalRange.min}-${sourceInfo.horizontalRange.max}`,
        questions_extracted: pdfQuestions,
        pages_processed: stats.totalPages,
        status: pdfStatus,
        error_message: errorMessage,
        cost_usd: pdfCost,
        started_at: pdfStartTime,
        completed_at: pdfEndTime,
      };
      await tracker.logExtraction(extractionLog);

      // Show running totals
      const costSummary = tracker.getCostSummary();
      await logger.info(
        `Questions: ${pdfQuestions} | Cost: $${pdfCost.toFixed(4)} | ` +
          `Total: ${costSummary.totalQuestions} Q, $${costSummary.total.toFixed(2)}`
      );
    }

    // Step 6: Final statistics
    await logger.info('\n' + '='.repeat(60));
    await logger.info('EXTRACTION COMPLETE');
    await logger.info('='.repeat(60));

    // Show comprehensive report from tracker
    const report = await tracker.generateReport();
    console.log(report);

    // Show error rate warning if needed
    const errorRate = tracker.getErrorRate();
    if (errorRate > ERROR_RATE_THRESHOLD) {
      await logger.warn(
        `Error rate (${errorRate.toFixed(1)}%) exceeds threshold (${ERROR_RATE_THRESHOLD}%)`
      );
      await logger.info('Failed PDFs:');
      const failedPdfs = tracker.getFailedPDFs();
      for (const pdf of failedPdfs.slice(0, 10)) {
        await logger.info(`  - ${pdf}`);
      }
      if (failedPdfs.length > 10) {
        await logger.info(`  ... and ${failedPdfs.length - 10} more`);
      }
    }

    // Get overall CSV stats
    const csvStats = await csvWriter.getStats();
    await logger.info('\n' + '='.repeat(60));
    await logger.info('QUESTION BANK STATISTICS');
    await logger.info('='.repeat(60));
    await logger.stats({
      'Total Questions in CSV': csvStats.totalQuestions,
      ...csvStats.bySource,
    });

  } catch (error) {
    await logger.error('Fatal error during extraction', error as Error);
    process.exit(1);
  }
}

// Run if called directly
if (import.meta.main) {
  main();
}
