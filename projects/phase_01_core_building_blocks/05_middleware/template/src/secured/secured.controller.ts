import { Controller, Get } from '@nestjs/common';
import { SecuredService } from './secured.service.js';

// Not part of this exercise.
@Controller('secured')
export class SecuredController {
  constructor(private readonly service: SecuredService) {}

  @Get()
  read(): { calls: number } {
    return { calls: this.service.hit() };
  }
}
