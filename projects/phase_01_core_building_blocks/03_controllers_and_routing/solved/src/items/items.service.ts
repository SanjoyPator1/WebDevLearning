import { Injectable } from '@nestjs/common';

export interface Item {
  id: number;
  name: string;
}

// Not part of this exercise: providers are topic 1.4. This is a tiny in-memory store so
// that the controllers have something to call. Read it, but you never edit it.
@Injectable()
export class ItemsService {
  private readonly items: Item[] = [
    { id: 1, name: 'apple' },
    { id: 2, name: 'banana' },
    { id: 3, name: 'cherry' },
  ];
  private nextId = 4;

  /** Items whose name contains `search` (all items when omitted), at most `limit` of them. */
  findAll(search?: string, limit?: number): Item[] {
    const found = search ? this.items.filter((item) => item.name.includes(search)) : [...this.items];
    return limit === undefined ? found : found.slice(0, limit);
  }

  findOne(id: number): Item | undefined {
    return this.items.find((item) => item.id === id);
  }

  create(name: string): Item {
    const item: Item = { id: this.nextId++, name };
    this.items.push(item);
    return item;
  }

  /** Renames the item. A missing `name` leaves it unchanged. Returns undefined for an unknown id. */
  rename(id: number, name?: string): Item | undefined {
    const item = this.findOne(id);
    if (item && name !== undefined) {
      item.name = name;
    }
    return item;
  }

  /** Creates the item with this exact id, or renames it when it already exists. */
  upsert(id: number, name: string): { item: Item; created: boolean } {
    const existing = this.findOne(id);
    if (existing) {
      existing.name = name;
      return { item: existing, created: false };
    }
    const item: Item = { id, name };
    this.items.push(item);
    return { item, created: true };
  }
}
