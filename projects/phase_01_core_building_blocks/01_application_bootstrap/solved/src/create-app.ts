import { type INestApplication, type LoggerService } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { ExpressAdapter } from '@nestjs/platform-express';
import { FastifyAdapter } from '@nestjs/platform-fastify';
import { AppModule } from './app.module.js';

export interface CreateAppOptions {
  /** HTTP adapter to run on. Default: 'express'. */
  adapter?: 'express' | 'fastify';
  /** Global route prefix, for example 'api'. Default: no prefix. */
  globalPrefix?: string;
  /** Routes that must NOT get the prefix, for example ['health']. Only used with globalPrefix. */
  excludeFromPrefix?: string[];
  /** CORS: true for defaults, an options object for specific origins. Default: CORS off. */
  cors?: boolean | { origin?: string | string[]; credentials?: boolean };
  /** Receives every Nest log line. When omitted, Nest stays silent. */
  logger?: LoggerService;
  /** Hold startup log lines until a logger is attached later with app.useLogger(). */
  bufferLogs?: boolean;
}

/**
 * Builds the application and returns it WITHOUT listening.
 * Topic 1.1: choosing the adapter, NestFactory.create options, global prefix, CORS and logging.
 */
export async function createApp(options: CreateAppOptions = {}): Promise<INestApplication> {
  const { adapter = 'express', globalPrefix, excludeFromPrefix = [], cors, logger, bufferLogs = false } = options;

  const httpAdapter = adapter === 'fastify' ? new FastifyAdapter() : new ExpressAdapter();

  const app = await NestFactory.create(AppModule, httpAdapter, {
    // No logger given means silent. With bufferLogs the lines written during create()
    // are still held back (even with `false`), and replayed to a logger attached later.
    logger: logger ?? false,
    bufferLogs,
    cors,
  });

  if (globalPrefix) {
    app.setGlobalPrefix(globalPrefix, { exclude: excludeFromPrefix });
  }

  return app;
}

/**
 * Starts listening and returns the URL.
 * Topic 1.1: PORT from the environment with a default, and a host that works inside a container.
 */
export async function startApp(
  app: INestApplication,
  env: Record<string, string | undefined> = process.env,
): Promise<string> {
  const port = Number(env.PORT ?? 3000);
  // 0.0.0.0 on purpose: Fastify's own default is loopback only, which a container cannot reach.
  const host = env.HOST ?? '0.0.0.0';

  await app.listen(port, host);
  return app.getUrl();
}
