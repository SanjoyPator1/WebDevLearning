import { Controller, Get } from '@nestjs/common';
import { OrderLog } from './order-log.js';

// Not part of this exercise: the handler writes "handler" into the log.
@Controller('order')
export class OrderController {
  constructor(private readonly log: OrderLog) {}

  @Get()
  run(): string {
    this.log.add('handler');
    return 'done';
  }
}
