import { BadRequestException, Controller, Get, HttpStatus, Param, ParseIntPipe } from '@nestjs/common';

// Task 3: the built-in Parse* pipes share two options.
//   errorHttpStatusCode  the status of the exception they throw (the body keeps the pipe's own
//                        message, and `error` becomes the matching name: "Unprocessable Entity")
//   exceptionFactory     a function that receives the pipe's message and returns the exception to
//                        throw. Use it to change the message or the body shape entirely.
// Both are per pipe INSTANCE, which is why these routes pass `new ParseIntPipe({...})`. Making the
// whole application answer errors the same way is the job of exception filters (1.9).
@Controller('strict')
export class StrictController {
  @Get('status/:id')
  status(
    @Param('id', new ParseIntPipe({ errorHttpStatusCode: HttpStatus.UNPROCESSABLE_ENTITY })) id: number,
  ): { id: number } {
    return { id };
  }

  @Get('named/:id')
  named(
    @Param('id', new ParseIntPipe({ exceptionFactory: () => new BadRequestException('id must be an integer') }))
    id: number,
  ): { id: number } {
    return { id };
  }
}
