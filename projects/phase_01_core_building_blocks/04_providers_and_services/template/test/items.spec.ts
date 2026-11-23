import { Test } from '@nestjs/testing';
import { DuplicateItemError, InvalidItemError, ItemNotFoundError } from '../src/items/items.errors.js';
import { ItemsRepository } from '../src/items/items.repository.js';
import { ItemsService } from '../src/items/items.service.js';

describe('Task 5: service, repository and helper', () => {
  let service: ItemsService;
  let repository: ItemsRepository;

  beforeEach(async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [ItemsRepository, ItemsService],
    }).compile();
    service = moduleRef.get(ItemsService);
    repository = moduleRef.get(ItemsRepository);
  });

  it('create() stores the normalized name', () => {
    expect(service.create('  Apple ')).toEqual({ id: 1, name: 'apple' });
  });

  it('create() rejects a name that is empty after trimming', () => {
    expect(() => service.create('   ')).toThrow(InvalidItemError);
    expect(service.list()).toEqual([]);
  });

  it('create() rejects a duplicate, whatever its case or spacing', () => {
    service.create('Apple');

    expect(() => service.create(' APPLE')).toThrow(DuplicateItemError);
    expect(service.list()).toHaveLength(1);
  });

  it('get() returns an item, or throws ItemNotFoundError', () => {
    const { id } = service.create('banana');

    expect(service.get(id)).toEqual({ id, name: 'banana' });
    expect(() => service.get(99)).toThrow(ItemNotFoundError);
  });

  it('list() returns every item', () => {
    service.create('apple');
    service.create('banana');

    expect(service.list().map((item) => item.name)).toEqual(['apple', 'banana']);
  });

  it('the service can be built by hand: no container is needed to test it', () => {
    const plain = new ItemsService(new ItemsRepository());

    expect(plain.create('Cherry').name).toBe('cherry');
  });

  it('guard: the repository has no rules, it stores whatever it is given', () => {
    repository.insert('same');
    repository.insert('same');
    repository.insert('');

    expect(repository.all()).toHaveLength(3);
  });
});
