import { BadRequestException, Controller, Get, UseInterceptors } from '@nestjs/common';
import { AuditLog } from '../common/audit-log.js';
import { ErrorMapperInterceptor } from './error-mapper.interceptor.js';
import { TimeoutInterceptor } from './timeout.interceptor.js';

// Not part of this exercise: the interceptors of Task 3 bound to routes.
@Controller('limits')
export class LimitsController {
  constructor(private readonly log: AuditLog) {}

  @Get('slow')
  @UseInterceptors(TimeoutInterceptor)
  async slow(): Promise<string> {
    await new Promise((resolve) => setTimeout(resolve, 200));
    this.log.add('slow-finished');
    return 'late';
  }

  @Get('fast')
  @UseInterceptors(TimeoutInterceptor)
  async fast(): Promise<string> {
    await new Promise((resolve) => setTimeout(resolve, 5));
    return 'quick';
  }

  @Get('fails')
  @UseInterceptors(TimeoutInterceptor)
  fails(): never {
    throw new BadRequestException('original');
  }

  @Get('upstream')
  @UseInterceptors(ErrorMapperInterceptor)
  upstream(): never {
    throw new Error('database password is hunter2');
  }

  @Get('bad')
  @UseInterceptors(ErrorMapperInterceptor)
  bad(): never {
    throw new BadRequestException('client mistake');
  }
}
