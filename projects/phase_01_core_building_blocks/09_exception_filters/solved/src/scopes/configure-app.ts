import type { INestApplication } from '@nestjs/common';
import { NamedFilter } from './named.filter.js';

// Task 5a: app.useGlobalFilters() binds filters to every route. It takes INSTANCES built with `new`,
// outside the container, so nothing is injected into them. For a global filter with dependencies use
// APP_FILTER (audit.module.ts).
export function configureApp(app: INestApplication): void {
  app.useGlobalFilters(new NamedFilter('global'));
}
