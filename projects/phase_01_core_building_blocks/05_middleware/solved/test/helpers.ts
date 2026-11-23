import type { INestApplication, NestApplicationOptions, Type } from '@nestjs/common';
import { Test } from '@nestjs/testing';

export interface TestApp {
  app: INestApplication;
  /** Every message Nest logged at warn level while booting and serving. */
  warnings: string[];
}

// Not part of this exercise: builds a real Nest application around the given modules, with an
// HTTP server you can call through supertest. Nothing listens on a port.
// `setup` runs BEFORE app.init(), which is the moment you would call app.use(...) in main.ts
// (middleware registered after init is ignored). The logger is replaced so that expected
// errors do not flood the output and so that tests can read the warnings Nest prints.
export async function createApp(
  modules: Type[],
  options: { setup?: (app: INestApplication) => void; app?: NestApplicationOptions } = {},
): Promise<TestApp> {
  const warnings: string[] = [];
  const logger = {
    log() {},
    error() {},
    warn(message: unknown) {
      warnings.push(String(message));
    },
  };

  const moduleRef = await Test.createTestingModule({ imports: modules }).compile();
  const app = moduleRef.createNestApplication({ logger, ...options.app });
  options.setup?.(app);
  await app.init();
  return { app, warnings };
}
