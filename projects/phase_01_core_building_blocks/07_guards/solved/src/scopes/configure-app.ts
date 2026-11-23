import type { INestApplication } from '@nestjs/common';
import { TraceGuard } from './trace.js';

// Task 5a: app.useGlobalGuards() binds guards to every route. It takes INSTANCES you build with
// `new`, outside the container, so nothing is injected into them. For a global guard with
// dependencies use the APP_GUARD provider (shop.module.ts).
export function configureApp(app: INestApplication): void {
  app.useGlobalGuards(new TraceGuard('global'));
}
