import { Module } from '@nestjs/common';
import { AsyncController } from './async/async.controller.js';
import { EchoController } from './echo/echo.controller.js';
import { ItemsController } from './items/items.controller.js';
import { ItemsService } from './items/items.service.js';
import { PathsController } from './paths/paths.controller.js';
import { ReplyController } from './reply/reply.controller.js';
import { ShelfController } from './shelf/shelf.controller.js';
import { StashController } from './stash/stash.controller.js';

// Not part of this exercise: modules are topic 1.2. One module lists every controller, so
// `pnpm start` serves them all once the tasks are done. Each task's tests build their own
// small module instead (see test/helpers.ts), so a half-finished controller never breaks
// another task's tests.
@Module({
  controllers: [
    ItemsController,
    EchoController,
    ReplyController,
    StashController,
    AsyncController,
    PathsController,
    ShelfController,
  ],
  providers: [ItemsService],
})
export class AppModule {}
