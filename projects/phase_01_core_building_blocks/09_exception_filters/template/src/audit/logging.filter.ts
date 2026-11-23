import type { ArgumentsHost } from '@nestjs/common';

// TODO(1.9) Task 4a
// A CATCH-ALL filter that records every exception and then lets Nest answer exactly as it would have.
//   - @Catch() with no arguments handles anything that is thrown (an Error, an HttpException, even a
//     string)
//   - extend BaseExceptionFilter from @nestjs/core: its catch() is Nest's own default handling (the
//     400 for an HttpException, the generic 500 for anything else, and the logging of unexpected errors)
//   - in your catch(exception, host): add one entry to ErrorLog (inject it through the constructor and
//     call super() in it), then call super.catch(exception, host)
//   - the entry is "<constructor name>: <message>", for example "Error: db down" or
//     "BadRequestException: bad". For a value that is not an Error use String(exception) as the message.
// Why extend BaseExceptionFilter instead of writing the response yourself? You keep the default
// behaviour for free, and it stays correct for whichever HTTP adapter the application uses.
export class LoggingFilter {
  catch(exception: unknown, host: ArgumentsHost): void {
    throw new Error('TODO(1.9) Task 4a: LoggingFilter');
  }
}
