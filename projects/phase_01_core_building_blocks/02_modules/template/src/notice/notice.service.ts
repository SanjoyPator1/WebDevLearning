import { Injectable } from '@nestjs/common';
import { LoggerService } from '../logger/logger.service.js';

// Not part of this exercise.
@Injectable()
export class NoticeService {
  constructor(private readonly logger: LoggerService) {}

  notify(message: string): void {
    this.logger.log(`notice: ${message}`);
  }
}
