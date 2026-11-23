import { Controller, Get, UseGuards } from '@nestjs/common';
import { TraceGuard, trace } from './trace.js';

// Task 5b: guards are collected from the widest scope to the narrowest, in this order:
//   global (app.useGlobalGuards)  ->  controller (@UseGuards on the class)  ->  method (@UseGuards on
//   the route)  and, inside one @UseGuards(a, b, c), left to right.
// They run ONE AT A TIME: Nest awaits each and stops at the first one that denies (returns a falsy
// value, or throws). The guards after it never run, and neither does anything else: the 403 on /two
// is produced after `first` and `second` only.
// Unlike pipes (1.6), a guard is not run per parameter: it runs once per request.
@Controller('scopes')
@UseGuards(new TraceGuard('controller'))
export class ScopesController {
  @Get('one')
  @UseGuards(new TraceGuard('method'))
  one(): string {
    trace.push('handler');
    return 'one';
  }

  @Get('two')
  @UseGuards(new TraceGuard('first'), new TraceGuard('second', false), new TraceGuard('third'))
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
