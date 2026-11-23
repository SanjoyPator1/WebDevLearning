import { Body, Controller, Get, Param, Post, Query } from '@nestjs/common';
import { ParsePositiveIntPipe } from './parse-positive-int.pipe.js';
import { TrimPipe } from './trim.pipe.js';

// Not part of this exercise: the pipes are already bound here. Task 4 is writing them.
@Controller('custom')
export class CustomController {
  @Get('param/:n')
  fromParam(@Param('n', ParsePositiveIntPipe) n: number): { n: number; type: string } {
    return { n, type: typeof n };
  }

  @Get('query')
  fromQuery(@Query('limit', ParsePositiveIntPipe) limit: number): { limit: number } {
    return { limit };
  }

  @Post('names')
  name(@Body('name', TrimPipe) name: unknown): { name: unknown } {
    return { name };
  }
}
