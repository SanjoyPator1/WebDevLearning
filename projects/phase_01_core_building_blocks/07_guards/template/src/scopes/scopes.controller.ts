import { Controller, Get } from '@nestjs/common';
import { trace } from './trace.js';

// TODO(1.7) Task 5b
// Bind TraceGuard (use instances: `new TraceGuard('controller')`) so that the trace of a request
// reads, for each route:
//   GET /scopes/one    global, controller, method, handler
//   GET /scopes/two    global, controller, first, second  and a 403: the second guard denies,
//                      so the third guard and the handler never run
//   GET /scopes/three  global, controller, handler
// Use three guards on `two`, named 'first', 'second' (which denies: second argument false) and
// 'third', in that order. Do not change the method bodies.
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
