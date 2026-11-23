import type { INestApplication } from '@nestjs/common';
import { TagPipe } from './tag.pipe.js';

// Task 5a: app.useGlobalPipes() binds pipes to every route of the application. It takes INSTANCES,
// so the pipe is built by you with `new`, outside the container: a global pipe registered this
// way cannot have dependencies injected. When a global pipe needs a provider, register it as a
// provider under the APP_PIPE token instead (custom providers, topic 2.2).
export function configureApp(app: INestApplication): void {
  app.useGlobalPipes(new TagPipe('G'));
}
