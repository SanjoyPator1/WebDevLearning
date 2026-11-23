import { Controller, Get } from '@nestjs/common';

// Not part of this exercise: a route for the global middleware of Task 1 to run in front of.
@Controller('hello')
export class HelloController {
  @Get()
  hello(): string {
    return 'hello';
  }
}
