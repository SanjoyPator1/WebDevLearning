import type { INestApplication } from '@nestjs/common';
import { TraceFilter, TraceGuard, TraceInterceptor, TracePipe, trace } from './components.js';

// Not part of this exercise: what main.ts would do. One component of each kind is registered globally.
export function configureLifecycle(app: INestApplication): void {
  app.use((req: unknown, res: unknown, next: () => void) => {
    trace.push('mw:global');
    next();
  });
  app.useGlobalGuards(new TraceGuard('global'));
  app.useGlobalInterceptors(new TraceInterceptor('global'));
  app.useGlobalPipes(new TracePipe('global'));
  app.useGlobalFilters(new TraceFilter('global'));
}
