import { Controller, Get } from '@nestjs/common';
import { EMPTY, defaultIfEmpty, from, toArray, type Observable } from 'rxjs';
import { sleep } from './sleep.js';

@Controller('async')
export class AsyncController {
  // 5a: an async handler returns a Promise. Nest awaits it, then sends the resolved value.
  @Get('later')
  async later(): Promise<{ waited: number }> {
    await sleep(20);
    return { waited: 20 };
  }

  // Not part of this exercise: a stream that emits three values, then completes.
  private stream(): Observable<{ step: number }> {
    return from([{ step: 1 }, { step: 2 }, { step: 3 }]);
  }

  // 5b: Nest sends only the LAST value an Observable emits (it uses lastValueFrom). Returned
  // as it is, this route would answer {"step":3}. toArray() collects every emission into one
  // array, which is emitted when the stream completes. To send values as they happen you need
  // Server-Sent Events (8.2), not a normal route.
  @Get('steps')
  steps(): Observable<unknown> {
    return this.stream().pipe(toArray());
  }

  // 5c: lastValueFrom rejects with EmptyError when the Observable completes without emitting,
  // and Nest answers 500. defaultIfEmpty(undefined) emits one value so there is a last value;
  // undefined is sent as an empty 200.
  @Get('nothing')
  nothing(): Observable<unknown> {
    return EMPTY.pipe(defaultIfEmpty(undefined));
  }
}
