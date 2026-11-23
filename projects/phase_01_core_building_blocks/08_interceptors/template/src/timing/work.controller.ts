import { BadRequestException, Controller, Get, Param, ParseIntPipe, UseInterceptors } from '@nestjs/common';
import { TimingInterceptor } from './timing.interceptor.js';

// Not part of this exercise: work that takes a chosen time, behind the interceptor of Task 2.
@Controller('work')
@UseInterceptors(TimingInterceptor)
export class WorkController {
  @Get('ok/:ms')
  async ok(@Param('ms', ParseIntPipe) ms: number): Promise<string> {
    await new Promise((resolve) => setTimeout(resolve, ms));
    return 'done';
  }

  @Get('fail')
  fail(): never {
    throw new BadRequestException('failed on purpose');
  }
}
