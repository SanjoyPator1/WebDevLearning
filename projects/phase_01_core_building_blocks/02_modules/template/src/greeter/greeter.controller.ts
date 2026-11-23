import { Controller, Get, Param } from '@nestjs/common';
import { GreeterService } from './greeter.service.js';

// Not part of this exercise: controllers and routing are topic 1.3. It exists so the
// end-to-end test has something to call.
@Controller('greet')
export class GreeterController {
  constructor(private readonly greeter: GreeterService) {}

  @Get(':name')
  greet(@Param('name') name: string): string {
    return this.greeter.greet(name);
  }
}
