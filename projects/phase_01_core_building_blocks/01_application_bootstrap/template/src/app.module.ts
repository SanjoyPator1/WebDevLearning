import { Module } from '@nestjs/common';
import { HealthController } from './health.controller.js';

// Not part of this exercise: modules are topic 1.2. This is the smallest module that has routes.
@Module({ controllers: [HealthController] })
export class AppModule {}
