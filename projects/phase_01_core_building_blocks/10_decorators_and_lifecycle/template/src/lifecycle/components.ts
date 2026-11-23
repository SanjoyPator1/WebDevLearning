import {
  type ArgumentsHost,
  BadRequestException,
  type CallHandler,
  type CanActivate,
  Catch,
  type ExceptionFilter,
  type ExecutionContext,
  HttpException,
  Injectable,
  type NestInterceptor,
  type NestMiddleware,
  type PipeTransform,
} from '@nestjs/common';
import { type Observable, tap } from 'rxjs';

// Not part of this exercise: components that only write their name into `trace`, and a few facts. They are
// bound by lifecycle.controller.ts, lifecycle.module.ts and configure-lifecycle.ts. Entries look like
//   mw:global  mw:module  guard:<scope>  before:<scope>  pipe:<scope>  handler
//   after:<scope>  error:<scope>  filter:<scope>
// where <scope> is global, controller, method or param.
export const trace: string[] = [];

export const facts: { statusInGuard?: number; statusInInterceptor?: number } = {};

export class TraceGuard implements CanActivate {
  constructor(
    private readonly scope: string,
    private readonly allow = true,
  ) {}

  canActivate(): boolean {
    trace.push(`guard:${this.scope}`);
    return this.allow;
  }
}

export class TraceInterceptor implements NestInterceptor {
  constructor(private readonly scope: string) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    trace.push(`before:${this.scope}`);
    return next.handle().pipe(
      tap({
        next: () => trace.push(`after:${this.scope}`),
        error: () => trace.push(`error:${this.scope}`),
      }),
    );
  }
}

export class TracePipe implements PipeTransform {
  constructor(
    private readonly scope: string,
    private readonly fail = false,
  ) {}

  transform(value: unknown): unknown {
    trace.push(`pipe:${this.scope}`);
    if (this.fail) throw new BadRequestException('pipe failed');
    return value;
  }
}

@Catch()
export class TraceFilter implements ExceptionFilter {
  constructor(private readonly scope: string) {}

  catch(exception: unknown, host: ArgumentsHost): void {
    trace.push(`filter:${this.scope}`);
    const status = exception instanceof HttpException ? exception.getStatus() : 500;
    host.switchToHttp().getResponse().status(status).json({ filteredBy: this.scope });
  }
}

@Injectable()
export class ModuleMiddleware implements NestMiddleware {
  use(req: unknown, res: unknown, next: () => void): void {
    trace.push('mw:module');
    next();
  }
}

// Records what the response looks like at two moments of the lifecycle (see the status route).
export class StatusGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    facts.statusInGuard = context.switchToHttp().getResponse().statusCode;
    return true;
  }
}

export class StatusInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    facts.statusInInterceptor = context.switchToHttp().getResponse().statusCode;
    return next.handle();
  }
}
