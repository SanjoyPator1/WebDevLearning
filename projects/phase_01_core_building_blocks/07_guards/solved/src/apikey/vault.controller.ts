import { Controller, Get, UseGuards } from '@nestjs/common';
import { CallCounter } from '../common/call-counter.js';
import { ApiKeyGuard } from './api-key.guard.js';

// Task 1b: @UseGuards() on the class applies the guard to every route of the controller; on a
// method it would apply to that route only. Passing the CLASS (`ApiKeyGuard`) lets Nest build it,
// once, in this module, and inject into it; passing `new ApiKeyGuard()` would hand over an instance
// you built yourself (fine here, but no injection). Guards run before the handler, so a denied
// request never reaches `counter.hit()`.
@Controller('vault')
@UseGuards(ApiKeyGuard)
export class VaultController {
  constructor(private readonly counter: CallCounter) {}

  @Get()
  open(): { secret: string; hit: number } {
    return { secret: 'swordfish', hit: this.counter.hit() };
  }

  @Get('keys')
  keys(): { keys: string[]; hit: number } {
    return { keys: ['k1', 'k2'], hit: this.counter.hit() };
  }
}
