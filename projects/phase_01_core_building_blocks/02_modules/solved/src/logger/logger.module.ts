import { Global, Module } from '@nestjs/common';
import { LoggerService } from './logger.service.js';

// @Global() makes Nest bind this module to EVERY module, so nobody has to import it. Two things
// still apply: the module must be imported once somewhere (the root module does that), and
// the provider must still be exported. Global does not mean "everything inside is public".
//
// The price is hidden dependencies: a module that uses LoggerService without importing
// LoggerModule looks complete but cannot be compiled or tested on its own. Reserve @Global()
// for things that truly every module needs (logging, configuration).
@Global()
@Module({
  providers: [LoggerService],
  exports: [LoggerService],
})
export class LoggerModule {}
