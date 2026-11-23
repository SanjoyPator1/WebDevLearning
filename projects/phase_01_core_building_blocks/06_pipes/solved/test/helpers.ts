import type { INestApplication, NestApplicationOptions, Provider, Type } from '@nestjs/common';
import { Test } from '@nestjs/testing';

export interface TestApp {
  app: INestApplication;
}

// Not part of this exercise: builds a real Nest application around the given controllers and
// providers, with an HTTP server you can call through supertest. Nothing listens on a port.
// `setup` runs BEFORE app.init(), which is where main.ts would call app.useGlobalPipes(...).
// The logger is replaced so that expected 400s and 500s do not flood the output.
export async function createApp(
  controllers: Type[],
  options: {
    providers?: Provider[];
    setup?: (app: INestApplication) => void;
    app?: NestApplicationOptions;
  } = {},
): Promise<TestApp> {
  const logger = { log() {}, error() {}, warn() {} };

  const moduleRef = await Test.createTestingModule({
    controllers,
    providers: options.providers ?? [],
  }).compile();

  const app = moduleRef.createNestApplication({ logger, ...options.app });
  options.setup?.(app);
  await app.init();
  return { app };
}
