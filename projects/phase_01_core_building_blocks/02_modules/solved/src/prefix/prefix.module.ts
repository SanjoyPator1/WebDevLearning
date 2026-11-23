import { DynamicModule, Module } from '@nestjs/common';
import { PREFIX_OPTIONS, PrefixOptions, PrefixService } from './prefix.service.js';

// A dynamic module is a module whose metadata is built at import time. The static @Module({})
// stays empty and forRoot() returns the same metadata shape plus a `module` property that
// says which class it belongs to. (The deep dive is topic 2.3.)
//
// Careful: Nest identifies a dynamic module by the OBJECT that forRoot() returns. Two
// forRoot() calls make two module instances, even with identical options.
@Module({})
export class PrefixModule {
  static forRoot(options: PrefixOptions): DynamicModule {
    return {
      module: PrefixModule,
      providers: [{ provide: PREFIX_OPTIONS, useValue: options }, PrefixService],
      exports: [PrefixService],
    };
  }
}
