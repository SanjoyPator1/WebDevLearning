import { Injectable, Module } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { CounterModule } from '../src/counter/counter.module.js';
import { CounterService } from '../src/counter/counter.service.js';
import { GreeterModule } from '../src/greeter/greeter.module.js';
import { GreeterService } from '../src/greeter/greeter.service.js';

describe('Task 1: CounterModule and GreeterModule', () => {
  beforeEach(() => {
    CounterService.created = 0;
  });

  it('GreeterModule compiles: GreeterService gets its CounterService from CounterModule', async () => {
    const moduleRef = await Test.createTestingModule({ imports: [GreeterModule] }).compile();

    const greeter = moduleRef.get(GreeterService);
    expect(greeter.greet('ada')).toBe('Hello, ada! (#1)');
    expect(greeter.greet('bob')).toBe('Hello, bob! (#2)');
  });

  it('CounterModule makes CounterService available to any module that imports it', async () => {
    @Injectable()
    class Consumer {
      constructor(readonly counter: CounterService) {}
    }
    @Module({ imports: [CounterModule], providers: [Consumer] })
    class ConsumerModule {}

    const moduleRef = await Test.createTestingModule({ imports: [ConsumerModule] }).compile();

    expect(moduleRef.get(Consumer).counter.next()).toBe(1);
  });
});
