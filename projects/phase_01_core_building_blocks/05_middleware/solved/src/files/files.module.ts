import { type MiddlewareConsumer, Module, type NestModule } from '@nestjs/common';
import { MarkMiddleware } from '../mark/mark.middleware.js';
import { FilesController } from './files.controller.js';

// Task 4: forRoutes() paths use the Express 5 syntax (path-to-regexp 8). A wildcard needs a
// name: `*splat` means "one or more segments", `{*splat}` means "zero or more". The old bare
// `files/*` still started because Nest rewrote it to `files/{*splat}` and logged a warning;
// `files/:id?` would have been a startup PathError. Here `files/*splat` is written the way it
// will stay valid. (Measured: neither form runs for the bare /files, and the mount is a
// prefix match, so /files/a/b is covered.)
@Module({ controllers: [FilesController] })
export class FilesModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(MarkMiddleware).forRoutes('files/*splat');
  }
}
