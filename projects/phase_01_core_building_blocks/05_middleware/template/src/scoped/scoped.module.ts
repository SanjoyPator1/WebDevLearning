import { Module } from '@nestjs/common';
import { ElsewhereController, ScopedController } from './scoped.controller.js';

// TODO(1.5) Task 3
// Implement NestModule and apply MarkMiddleware (src/mark/mark.middleware.ts) with the right
// routes:
//   - every route of ScopedController gets it, with ONE exception:
//   - GET /scoped/health does not. POST /scoped/health still does.
//   - ElsewhereController does not get it.
// Look at how a route can be described by path AND method, and at the consumer's exclude().
@Module({ controllers: [ScopedController, ElsewhereController] })
export class ScopedModule {}
