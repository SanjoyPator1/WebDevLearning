import { Injectable } from '@nestjs/common';

export interface Item {
  id: number;
  name: string;
}

// Not part of this exercise: a repository only stores and fetches. It has NO rules. It will
// happily insert the same name twice or an empty name: deciding that is the service's job
// (Task 5). The data lives in an array here; a real one would talk to a database (4.2).
@Injectable()
export class ItemsRepository {
  private readonly items: Item[] = [];
  private nextId = 1;

  insert(name: string): Item {
    const item: Item = { id: this.nextId++, name };
    this.items.push(item);
    return item;
  }

  all(): Item[] {
    return [...this.items];
  }

  findById(id: number): Item | undefined {
    return this.items.find((item) => item.id === id);
  }

  findByName(name: string): Item | undefined {
    return this.items.find((item) => item.name === name);
  }
}
