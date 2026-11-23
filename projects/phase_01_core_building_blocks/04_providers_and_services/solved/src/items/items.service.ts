import { Injectable } from '@nestjs/common';
import { DuplicateItemError, InvalidItemError, ItemNotFoundError } from './items.errors.js';
import { ItemsRepository, type Item } from './items.repository.js';
import { normalizeName } from './normalize-name.js';

// Task 5: who does what.
//
//   service     business rules and orchestration: what is a valid name, what counts as a
//               duplicate, what happens when something is missing. This class.
//   repository  storing and fetching, nothing else. No rules (see the guard test).
//   helper      a pure function with no state and no dependencies: imported, not injected.
//   errors      domain errors. They say WHAT went wrong, not which HTTP status it becomes:
//               that mapping belongs to the edge of the application (1.9).
//
// The constructor takes the repository, so the service works with Nest and also by hand:
// `new ItemsService(new ItemsRepository())` is a complete unit test setup. @Injectable() is
// what makes Nest fill that parameter; without it, `repository` would be undefined and the
// first call would fail with a TypeError that never mentions the decorator.
@Injectable()
export class ItemsService {
  constructor(private readonly repository: ItemsRepository) {}

  create(name: string): Item {
    const normalized = normalizeName(name);
    if (normalized === '') {
      throw new InvalidItemError();
    }
    if (this.repository.findByName(normalized)) {
      throw new DuplicateItemError(normalized);
    }
    return this.repository.insert(normalized);
  }

  get(id: number): Item {
    const item = this.repository.findById(id);
    if (!item) {
      throw new ItemNotFoundError(id);
    }
    return item;
  }

  list(): Item[] {
    return this.repository.all();
  }
}
