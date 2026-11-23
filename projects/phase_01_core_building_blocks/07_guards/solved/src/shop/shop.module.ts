import { Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { DocsController, ShopController } from './shop.controller.js';
import { TokenRequiredGuard } from './token-required.guard.js';

// Task 4c: two ways to make a guard global, and only one has injection.
//   app.useGlobalGuards(new Guard())   an instance built outside the container: nothing is injected
//                                      (measured: a guard with a missing dependency answers 500)
//   { provide: APP_GUARD, useClass }   a provider Nest builds like any other, so the guard can
//                                      inject the Reflector and your services. Nest finds every
//                                      provider with this token, in ANY module, and applies it to
//                                      the whole application: the module it sits in only decides
//                                      what the guard can inject, not where it applies.
// A global guard registered this way does not run for a path that matches no route (a 404).
@Module({
  controllers: [ShopController, DocsController],
  providers: [{ provide: APP_GUARD, useClass: TokenRequiredGuard }],
})
export class ShopModule {}
