import { MiddlewareConsumer, Module, NestModule } from '@nestjs/common';
import { OrderController } from './order.controller.js';
import { OrderLog } from './order-log.js';
import { First, Second, Third } from './stages.js';

// TODO(1.5) Task 5
// A request must be seen in this order: the global middleware the test registers with
// app.use(), then First, Second, Third, then the handler. The configuration below lists them
// in the wrong order. Run test/order.spec.ts, read the log in the failure message, and fix
// the configuration. Find out two things: does the order inside apply(...) matter, and does
// the order of separate apply(...) calls matter?
@Module({
  controllers: [OrderController],
  providers: [OrderLog],
})
export class OrderModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(Third).forRoutes(OrderController);
    consumer.apply(Second, First).forRoutes(OrderController);
  }
}
