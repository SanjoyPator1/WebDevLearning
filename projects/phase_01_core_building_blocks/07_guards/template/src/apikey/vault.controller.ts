import { Controller, Get } from '@nestjs/common';
import { CallCounter } from '../common/call-counter.js';

// TODO(1.7) Task 1b
// Protect EVERY route of this controller with ApiKeyGuard, by binding it once on the class.
// Bind the CLASS (not `new ApiKeyGuard()`): Nest builds it and can inject into it.
// Do not change the method bodies.
@Controller('vault')
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
