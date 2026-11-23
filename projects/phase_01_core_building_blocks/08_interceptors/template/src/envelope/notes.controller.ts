import { BadRequestException, Controller, Get, UseInterceptors } from '@nestjs/common';
import { EnvelopeInterceptor } from './envelope.interceptor.js';

// Not part of this exercise: handlers that return different kinds of values, behind the
// interceptor of Task 1 (bound once on the class).
@Controller('notes')
@UseInterceptors(EnvelopeInterceptor)
export class NotesController {
  @Get('list')
  list(): Array<{ id: number }> {
    return [{ id: 1 }, { id: 2 }];
  }

  @Get('one')
  one(): { id: number; text: string } {
    return { id: 1, text: 'hello' };
  }

  @Get('text')
  text(): string {
    return 'plain';
  }

  @Get('none')
  none(): void {}

  @Get('later')
  async later(): Promise<number> {
    await new Promise((resolve) => setTimeout(resolve, 5));
    return 7;
  }

  @Get('bad')
  bad(): never {
    throw new BadRequestException('nope');
  }
}
