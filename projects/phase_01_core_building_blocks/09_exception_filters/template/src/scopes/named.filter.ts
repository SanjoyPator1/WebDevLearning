import { type ArgumentsHost, Catch, type ExceptionFilter, HttpException } from '@nestjs/common';

// Not part of this exercise: every NamedFilter that runs writes its name into this array, and answers with
// { by: <its name> }, so the tests can read which filter handled an exception.
export const trace: string[] = [];

@Catch()
export class NamedFilter implements ExceptionFilter {
  constructor(private readonly name: string) {}

  catch(exception: unknown, host: ArgumentsHost): void {
    trace.push(this.name);
    const status = exception instanceof HttpException ? exception.getStatus() : 500;
    host.switchToHttp().getResponse().status(status).json({ by: this.name });
  }
}
