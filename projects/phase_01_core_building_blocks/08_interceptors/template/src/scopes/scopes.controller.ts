import { Controller, Get } from '@nestjs/common';
import { trace } from './named.interceptor.js';

// TODO(1.8) Task 5b
// Bind NamedInterceptor (instances: `new NamedInterceptor('controller')`) so that the trace of each
// route reads, in and out:
//   GET /scopes/one    global:before, controller:before, method:before, handler,
//                      method:after, controller:after, global:after
//   GET /scopes/two    global:before, controller:before, first:before, second:before, handler,
//                      second:after, first:after, controller:after, global:after
//   GET /scopes/three  global:before, controller:before, handler, controller:after, global:after
// For `two` use two interceptors on the route, 'first' and 'second', in one @UseInterceptors.
// Notice how the "after" half is the mirror image of the "before" half. Do not change the bodies.
@Controller('scopes')
export class ScopesController {
  @Get('one')
  one(): string {
    trace.push('handler');
    return 'one';
  }

  @Get('two')
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
