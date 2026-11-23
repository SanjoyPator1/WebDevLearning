import type { INestApplication, NestApplicationOptions, Provider, Type } from '@nestjs/common';
import { Test } from '@nestjs/testing';

// Not part of this exercise: builds a real Nest application around the given modules, controllers
// and providers, with an HTTP server you can call through supertest. Nothing listens on a port.
// `setup` runs BEFORE app.init(), which is where main.ts would call app.useGlobalInterceptors(...).
// The logger is replaced so that expected 401s, 403s and 500s do not flood the output.
export async function createApp(
  options: {
    imports?: Type[];
    controllers?: Type[];
    providers?: Provider[];
    setup?: (app: INestApplication) => void;
    app?: NestApplicationOptions;
  } = {},
): Promise<INestApplication> {
  const logger = { log() {}, error() {}, warn() {} };

  const moduleRef = await Test.createTestingModule({
    imports: options.imports ?? [],
    controllers: options.controllers ?? [],
    providers: options.providers ?? [],
  }).compile();

  const app = moduleRef.createNestApplication({ logger, ...options.app });
  options.setup?.(app);
  await app.init();
  return app;
}
