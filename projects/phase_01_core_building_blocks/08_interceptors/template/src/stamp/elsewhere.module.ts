import { Controller, Get, Module } from '@nestjs/common';

@Controller('elsewhere')
export class ElsewhereController {
  @Get()
  get(): string {
    return 'elsewhere';
  }
}

// Not part of this exercise: a module that never imports StampModule, to show how far a global
// interceptor reaches.
@Module({ controllers: [ElsewhereController] })
export class ElsewhereModule {}
