import { DynamicModule, Module } from '@nestjs/common';
import { PREFIX_OPTIONS, PrefixOptions, PrefixService } from './prefix.service.js';

// TODO(1.2) Task 6
// Turn PrefixModule into a dynamic module: forRoot(options) must return a DynamicModule
// that makes PrefixOptions available under the PREFIX_OPTIONS token, provides PrefixService
// and exports it. (The imports above are the ones the solution needs.)
@Module({})
export class PrefixModule {
  static forRoot(options: PrefixOptions): DynamicModule {
    void PREFIX_OPTIONS;
    void PrefixService;
    void options;
    throw new Error('TODO(1.2): implement PrefixModule.forRoot');
  }
}
