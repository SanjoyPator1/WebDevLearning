import { Injectable } from '@nestjs/common';

// Not part of this exercise: a provider (topic 1.4) that the pipe of Task 6 needs.
@Injectable()
export class CatalogService {
  private readonly products = new Map<string, string>([
    ['A1', 'Anvil'],
    ['B2', 'Bellows'],
  ]);

  find(sku: string): string | undefined {
    return this.products.get(sku);
  }

  add(sku: string, name: string): void {
    this.products.set(sku, name);
  }
}
