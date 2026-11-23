import { Test } from '@nestjs/testing';
import { PrefixModule } from '../src/prefix/prefix.module.js';
import { PrefixService } from '../src/prefix/prefix.service.js';

describe('Task 6: a dynamic module', () => {
  it('forRoot returns a DynamicModule that names PrefixModule', () => {
    const dynamic = PrefixModule.forRoot({ prefix: '> ' });

    expect(dynamic.module).toBe(PrefixModule);
  });

  it('PrefixService uses the options given to forRoot', async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [PrefixModule.forRoot({ prefix: 'A:' })],
    }).compile();

    expect(moduleRef.get(PrefixService).format('x')).toBe('A:x');
  });

  it('every forRoot call configures its own app', async () => {
    const first = await Test.createTestingModule({ imports: [PrefixModule.forRoot({ prefix: '1-' })] }).compile();
    const second = await Test.createTestingModule({ imports: [PrefixModule.forRoot({ prefix: '2-' })] }).compile();

    expect(first.get(PrefixService).format('y')).toBe('1-y');
    expect(second.get(PrefixService).format('y')).toBe('2-y');
  });
});
