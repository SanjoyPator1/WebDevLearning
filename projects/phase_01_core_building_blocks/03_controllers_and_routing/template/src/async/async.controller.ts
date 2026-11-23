import { Controller, Get } from '@nestjs/common';
import { EMPTY, from, type Observable } from 'rxjs';
import { sleep } from './sleep.js';

// The routes are given. Nest accepts a plain value, a Promise or an Observable from a handler.
// TODO(1.3) Task 5: make each handler answer what its comment says.
@Controller('async')
export class AsyncController {
  // TODO(1.3) Task 5a: wait for sleep(20), then answer { "waited": 20 }.
  @Get('later')
  later(): Promise<{ waited: number }> {
    throw new Error('TODO(1.3) Task 5a: later');
  }

  // Not part of this exercise: a stream that emits three values, then completes.
  private stream(): Observable<{ step: number }> {
    return from([{ step: 1 }, { step: 2 }, { step: 3 }]);
  }

  // TODO(1.3) Task 5b: answer [{"step":1},{"step":2},{"step":3}].
  // Run the test first and read what the client gets today. Then find the rxjs operator
  // that collects every emitted value into one array. Operators are topic 1.8, so use
  // only the one you need.
  @Get('steps')
  steps(): Observable<unknown> {
    return this.stream();
  }

  // TODO(1.3) Task 5c: answer 200 with an empty body.
  // The Observable below completes without emitting. Run the test and read what happens.
  // Fix it without replacing EMPTY.
  @Get('nothing')
  nothing(): Observable<unknown> {
    return EMPTY;
  }
}
