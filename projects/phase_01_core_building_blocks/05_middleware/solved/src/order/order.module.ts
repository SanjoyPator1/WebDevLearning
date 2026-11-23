import { type MiddlewareConsumer, Module, type NestModule } from '@nestjs/common';
import { OrderController } from './order.controller.js';
import { OrderLog } from './order-log.js';
import { First, Second, Third } from './stages.js';

// Task 5: middleware runs in the order it was registered, as Express does.
//   - inside apply(A, B) the order of the arguments is the order they run in
//   - separate apply() calls in one configure() run in the order of the calls
//   - global app.use() middleware runs first of all, before any module's middleware
//   - between modules: global modules first, then the modules closest to the root, then
//     deeper ones; siblings at the same depth in import order (see the notes)
// A request therefore runs: global, First, Second, Third, then the handler. Either of the
// two spellings below gives the same order.
@Module({
  controllers: [OrderController],
  providers: [OrderLog],
})
export class OrderModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(First, Second).forRoutes(OrderController);
    consumer.apply(Third).forRoutes(OrderController);
  }
}
