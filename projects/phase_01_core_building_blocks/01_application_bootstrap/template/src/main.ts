import { ConsoleLogger } from '@nestjs/common';
import { createApp, startApp } from './create-app.js';

// Not part of this exercise: the entry point only wires your two functions together.
// Run it with `pnpm start`, for example `PORT=4000 pnpm start`, then `curl http://127.0.0.1:4000/api/version`.
const app = await createApp({
  globalPrefix: 'api',
  excludeFromPrefix: ['health'],
  cors: true,
  logger: new ConsoleLogger(),
});
const url = await startApp(app, process.env);
console.log(`Listening on ${url}`);
