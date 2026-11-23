import { ItemsRepository, type Item } from './items.repository.js';
import { DuplicateItemError, InvalidItemError, ItemNotFoundError } from './items.errors.js';
import { normalizeName } from './normalize-name.js';

// TODO(1.4) Task 5
// The service is where the business rules live. The repository stores what it is given, the
// helper normalizeName() is a plain function, and the errors are in items.errors.ts.
//   1. This class has its constructor but is not a provider yet. Run the tests and read what
//      happens when you call a method: nothing says "missing decorator". Fix it.
//   2. create(name):
//        - normalize the name with normalizeName()
//        - an empty result throws InvalidItemError
//        - a name that already exists (repository.findByName) throws DuplicateItemError
//        - otherwise store the NORMALIZED name through the repository and return the item
//   3. get(id): the item, or throws ItemNotFoundError
//   4. list(): every item
// Do not put any of these rules in the repository.
export class ItemsService {
  constructor(private readonly repository: ItemsRepository) {}

  create(name: string): Item {
    void [normalizeName, InvalidItemError, DuplicateItemError, this.repository]; // remove when used
    throw new Error('TODO(1.4) Task 5: create');
  }

  get(id: number): Item {
    void [ItemNotFoundError, id]; // remove when used
    throw new Error('TODO(1.4) Task 5: get');
  }

  list(): Item[] {
    throw new Error('TODO(1.4) Task 5: list');
  }
}
