import type { INestApplication, NestApplicationOptions, Provider, Type } from '@nestjs/common';
import { Test } from '@nestjs/testing';

export interface TestApp {
  app: INestApplication;
  /** Every message Nest logged at warn level while booting and serving. */
  warnings: string[];
}

// Not part of this exercise: builds a real Nest application around the given controllers,
// with an HTTP server you can call through supertest. Nothing is listening on a port.
// The logger is replaced so that expected 500s do not flood the output, and so that tests
// can read the warnings Nest prints.
export async function createApp(
  controllers: Type[],
  options: { providers?: Provider[]; app?: NestApplicationOptions } = {},
): Promise<TestApp> {
  const warnings: string[] = [];
  const logger = {
    log() {},
    error() {},
    warn(message: unknown) {
      warnings.push(String(message));
    },
  };

  const moduleRef = await Test.createTestingModule({
    controllers,
    providers: options.providers ?? [],
  }).compile();

  const app = moduleRef.createNestApplication({ logger, ...options.app });
  await app.init();
  return { app, warnings };
}
