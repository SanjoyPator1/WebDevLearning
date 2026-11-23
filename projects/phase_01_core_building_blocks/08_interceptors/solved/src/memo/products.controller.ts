import { Controller, Get, Injectable, Param, UseInterceptors } from '@nestjs/common';
import { Cached } from './cached.decorator.js';
import { MemoInterceptor } from './memo.interceptor.js';

// Not part of this exercise: counts how many times a handler really ran.
@Injectable()
export class ProductCounter {
  calls = 0;
}

@Controller('products')
@UseInterceptors(MemoInterceptor)
export class ProductsController {
  constructor(private readonly counter: ProductCounter) {}

  // Not cached: no @Cached(), the handler runs every time.
  @Get('live')
  live(): { n: number } {
    return { n: ++this.counter.calls };
  }

  @Get(':id')
  @Cached()
  one(@Param('id') id: string): { id: string; n: number } {
    return { id, n: ++this.counter.calls };
  }
}
