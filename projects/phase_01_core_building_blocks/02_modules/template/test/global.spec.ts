import { ModulesContainer } from '@nestjs/core';
import { Test } from '@nestjs/testing';
import { LoggerModule } from '../src/logger/logger.module.js';
import { LoggerService } from '../src/logger/logger.service.js';
import { NoticeModule } from '../src/notice/notice.module.js';
import { NoticeService } from '../src/notice/notice.service.js';

describe('Task 4: a global module', () => {
  it('NoticeModule uses LoggerService without importing LoggerModule, because LoggerModule is global', async () => {
    const moduleRef = await Test.createTestingModule({ imports: [LoggerModule, NoticeModule] }).compile();

    moduleRef.get(NoticeService).notify('hello');

    expect(moduleRef.get(LoggerService).lines).toEqual(['notice: hello']);
  });

  // The price of global modules: NoticeModule looks complete but cannot work on its own.
  it('the hidden dependency: NoticeModule alone cannot compile', async () => {
    await expect(Test.createTestingModule({ imports: [NoticeModule] }).compile()).rejects.toThrow(
      /Nest can't resolve dependencies of the NoticeService/,
    );
  });

  it('Nest records LoggerModule as global in its module container', async () => {
    const moduleRef = await Test.createTestingModule({ imports: [LoggerModule] }).compile();

    const modules = [...moduleRef.get(ModulesContainer).values()];
    expect(modules.find((m) => m.metatype === LoggerModule)?.isGlobal).toBe(true);
  });
});
