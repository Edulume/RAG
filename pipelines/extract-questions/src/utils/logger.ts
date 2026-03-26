/**
 * Simple logger utility for tracking extraction progress and errors
 */

import { writeFile, appendFile, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import { config } from '../config/settings.js';

export class Logger {
  private logFile: string;
  private errorFile: string;

  constructor(sessionId: string) {
    const logDir = config.paths.logDir;

    // Create log directory if it doesn't exist
    if (!existsSync(logDir)) {
      mkdir(logDir, { recursive: true });
    }

    const timestamp = new Date().toISOString().split('T')[0];
    this.logFile = join(logDir, `extraction-${timestamp}-${sessionId}.log`);
    this.errorFile = join(logDir, `errors-${timestamp}-${sessionId}.log`);
  }

  private formatMessage(level: string, message: string): string {
    const timestamp = new Date().toISOString();
    return `[${timestamp}] [${level}] ${message}\n`;
  }

  async info(message: string): Promise<void> {
    const formatted = this.formatMessage('INFO', message);
    console.log(formatted.trim());
    await appendFile(this.logFile, formatted);
  }

  async success(message: string): Promise<void> {
    const formatted = this.formatMessage('SUCCESS', `✓ ${message}`);
    console.log(formatted.trim());
    await appendFile(this.logFile, formatted);
  }

  async warn(message: string): Promise<void> {
    const formatted = this.formatMessage('WARN', `⚠ ${message}`);
    console.warn(formatted.trim());
    await appendFile(this.logFile, formatted);
  }

  async error(message: string, error?: Error): Promise<void> {
    const errorMsg = error ? `${message}: ${error.message}` : message;
    const formatted = this.formatMessage('ERROR', `✗ ${errorMsg}`);
    console.error(formatted.trim());
    await appendFile(this.logFile, formatted);
    await appendFile(this.errorFile, formatted);

    if (error?.stack) {
      await appendFile(this.errorFile, error.stack + '\n');
    }
  }

  async stats(stats: Record<string, number | string>): Promise<void> {
    const message = Object.entries(stats)
      .map(([key, value]) => `${key}: ${value}`)
      .join(', ');
    await this.info(`STATS - ${message}`);
  }
}
