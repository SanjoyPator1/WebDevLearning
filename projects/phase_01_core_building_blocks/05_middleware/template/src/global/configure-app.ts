import type { INestApplication } from '@nestjs/common';

// TODO(1.5) Task 1b
// This is the code that would sit in main.ts, between NestFactory.create() and listen().
// Register tagResponse as GLOBAL middleware, so that it runs for every request.
// The tests call this function before the application is initialised.
export function configureApp(app: INestApplication): void {
  throw new Error('TODO(1.5) Task 1b: configureApp');
}
