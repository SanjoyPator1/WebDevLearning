import { type INestApplication, type LoggerService } from '@nestjs/common';
// TODO(1.1): you will need NestFactory from '@nestjs/core', ExpressAdapter from
// '@nestjs/platform-express' and FastifyAdapter from '@nestjs/platform-fastify'.
// import { AppModule } from './app.module.js';  (Not part of this exercise: AppModule already exists)

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
export async function createApp(_options: CreateAppOptions = {}): Promise<INestApplication> {
  // TODO(1.1): see the numbered tasks 1 to 5 in the README.
  //  - pick the adapter (default express)
  //  - call NestFactory.create with the adapter and the options that map to Nest's own
  //    (logger, bufferLogs, cors). "No logger given" must mean "silent".
  //  - set the global prefix, with the excluded routes
  //  - return the app WITHOUT calling listen
  throw new Error('TODO(1.1): implement createApp');
}

/**
 * Starts listening and returns the URL.
 * Topic 1.1: PORT from the environment with a default, and a host that works inside a container.
 */
export async function startApp(
  _app: INestApplication,
  _env: Record<string, string | undefined> = process.env,
): Promise<string> {
  // TODO(1.1): see task 6 in the README.
  //  - port: Number(env.PORT) with a default of 3000
  //  - host: env.HOST with a default that a container can reach
  //  - listen, then return the URL Nest reports
  throw new Error('TODO(1.1): implement startApp');
}
