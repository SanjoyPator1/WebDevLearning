import { Controller, Get, UseInterceptors } from '@nestjs/common';
import { NamedInterceptor, trace } from './named.interceptor.js';

// Task 5b: interceptors nest like Russian dolls. They are collected from the widest scope to the
// narrowest (global, controller, method; left to right inside one @UseInterceptors), and the first one
// is the OUTERMOST. Each interceptor's "before" runs on the way in, in that order, then the handler,
// then each one's "after" runs on the way out in the REVERSE order, because the value travels back
// through the same layers. That is the difference from guards (1.7) and pipes (1.6), which only have
// a forward direction.
// Typical consequence: an outer timing interceptor measures the inner ones too, and an inner mapping
// interceptor reshapes the value before an outer one sees it.
@Controller('scopes')
@UseInterceptors(new NamedInterceptor('controller'))
export class ScopesController {
  @Get('one')
  @UseInterceptors(new NamedInterceptor('method'))
  one(): string {
    trace.push('handler');
    return 'one';
  }

  @Get('two')
  @UseInterceptors(new NamedInterceptor('first'), new NamedInterceptor('second'))
  two(): string {
    trace.push('handler');
    return 'two';
  }

  @Get('three')
  three(): string {
    trace.push('handler');
    return 'three';
  }
}
