import { Test } from '@nestjs/testing';
import { GreeterService } from '../src/greeter/greeter.service.js';

describe('Task 2: a singleton must not keep per-call state', () => {
  let greeter: GreeterService;

  beforeEach(async () => {
    const moduleRef = await Test.createTestingModule({ providers: [GreeterService] }).compile();
    greeter = moduleRef.get(GreeterService);
  });

  it('a single call works', async () => {
    await expect(greeter.greet('ada', 1)).resolves.toBe('hello ada');
  });

  it('two overlapping calls each answer their own name', async () => {
    const results = await Promise.all([greeter.greet('ada', 30), greeter.greet('bob', 5)]);

    expect(results).toEqual(['hello ada', 'hello bob']);
  });

  it('many overlapping calls never mix up their names', async () => {
    const names = ['ada', 'bob', 'cy', 'di', 'ed'];

    const results = await Promise.all(names.map((name, i) => greeter.greet(name, (names.length - i) * 5)));

    expect(results).toEqual(names.map((name) => `hello ${name}`));
  });

  it('the instance keeps no field that changes from call to call', () => {
    expect(Object.keys(greeter)).toEqual([]);
  });
});
