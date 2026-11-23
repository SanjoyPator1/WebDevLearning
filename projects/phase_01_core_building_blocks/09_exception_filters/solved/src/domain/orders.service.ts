import { Injectable } from '@nestjs/common';
import {
  DiscontinuedError,
  InvalidQuantityError,
  OutOfStockError,
  UnknownProductError,
} from './domain-errors.js';

// Not part of this exercise: a service that throws DOMAIN errors only, and has no idea they will become
// HTTP responses.
@Injectable()
export class OrdersService {
  order(sku: string, quantity: number): { sku: string; quantity: number } {
    if (quantity <= 0) throw new InvalidQuantityError(quantity);
    if (sku === 'ghost') throw new UnknownProductError(sku);
    if (sku === 'empty') throw new OutOfStockError(sku);
    if (sku === 'old') throw new DiscontinuedError(sku);
    if (sku === 'boom') throw new Error('connection to the database was lost');
    return { sku, quantity };
  }
}
