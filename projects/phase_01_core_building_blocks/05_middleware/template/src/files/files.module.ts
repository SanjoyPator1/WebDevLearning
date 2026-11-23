import { MiddlewareConsumer, Module, NestModule } from '@nestjs/common';
import { MarkMiddleware } from '../mark/mark.middleware.js';
import { FilesController } from './files.controller.js';

// TODO(1.5) Task 4
// forRoutes() takes route paths, and they follow the same Express 5 syntax as @Get(). The path
// below uses the pre-Express-5 wildcard: Nest still starts, because it converts the path and
// prints a warning. Rewrite it in the Express 5 syntax so that nothing is converted.
// MarkMiddleware must still run for /files/a/b, and still not for /files itself.
@Module({ controllers: [FilesController] })
export class FilesModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(MarkMiddleware).forRoutes('files/*');
  }
}
