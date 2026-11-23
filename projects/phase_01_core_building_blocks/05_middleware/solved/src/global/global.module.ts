import { Module } from '@nestjs/common';
import { HelloController } from './hello.controller.js';

// Not part of this exercise: modules are topic 1.2.
@Module({ controllers: [HelloController] })
export class GlobalModule {}
