import type { INestApplication } from '@nestjs/common';
import { NamedInterceptor } from './named.interceptor.js';

// Task 5a: app.useGlobalInterceptors() binds interceptors to every route. It takes INSTANCES you build
// with `new`, outside the container, so nothing is injected into them (measured: an interceptor with a
// missing dependency answers 500). For a global interceptor with dependencies use APP_INTERCEPTOR
// (stamp.module.ts).
export function configureApp(app: INestApplication): void {
  app.useGlobalInterceptors(new NamedInterceptor('global'));
}
