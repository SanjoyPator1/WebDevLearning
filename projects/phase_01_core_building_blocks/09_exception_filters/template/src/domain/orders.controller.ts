import { Controller, Get, Param, ParseIntPipe, UseFilters } from '@nestjs/common';
import { DomainErrorFilter } from './domain-error.filter.js';
import { OrdersService } from './orders.service.js';

// Not part of this exercise: a thin controller. It does not catch anything and knows no statuses: the
// filter of Task 3 is bound once on the class.
@Controller('orders')
@UseFilters(DomainErrorFilter)
export class OrdersController {
  constructor(private readonly orders: OrdersService) {}

  @Get(':sku/:quantity')
  order(
    @Param('sku') sku: string,
    @Param('quantity', ParseIntPipe) quantity: number,
  ): { sku: string; quantity: number } {
    return this.orders.order(sku, quantity);
  }
}
