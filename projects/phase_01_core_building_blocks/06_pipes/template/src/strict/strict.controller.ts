import { Controller, Get, Param } from '@nestjs/common';

// TODO(1.6) Task 3
// Built-in pipes take an options object that changes the error they throw.
//   GET /strict/status/:id   id must be an integer; a bad value answers 422 (not 400),
//                            with the pipe's own default message
//   GET /strict/named/:id    id must be an integer; a bad value answers 400 with the message
//                            "id must be an integer" instead of the pipe's default
// Look at the options of ParseIntPipe: one is a status code, one builds the exception.
@Controller('strict')
export class StrictController {
  @Get('status/:id')
  status(@Param('id') id: number): { id: number } {
    return { id };
  }

  @Get('named/:id')
  named(@Param('id') id: number): { id: number } {
    return { id };
  }
}
