import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

// Not part of this exercise: bootstrapping is topic 1.1.
const app = await NestFactory.create(AppModule);
await app.listen(process.env.PORT ?? 3000);
