import { Module } from '@nestjs/common';
import { DocsController, ShopController } from './shop.controller.js';

// TODO(1.7) Task 4c
// Register TokenRequiredGuard as a GLOBAL guard that Nest builds with dependency injection:
// add a provider to this module under the APP_GUARD token (exported by @nestjs/core), using
// `useClass`. Unlike app.useGlobalGuards(new Guard()), which takes an instance you built outside
// the container, a guard registered this way can inject the Reflector and any provider.
// (A provider of the form { provide, useClass } is a custom provider, topic 2.2: copy the shape.)
@Module({ controllers: [ShopController, DocsController] })
export class ShopModule {}
