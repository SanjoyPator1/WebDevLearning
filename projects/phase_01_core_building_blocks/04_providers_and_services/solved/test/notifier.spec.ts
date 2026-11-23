import { Test } from '@nestjs/testing';
import { LoudNotifierService } from '../src/notifier/loud-notifier.service.js';
import { NotifierService } from '../src/notifier/notifier.service.js';
import { SlackClient } from '../src/notifier/slack.client.js';

describe('Task 4a: @Optional()', () => {
  it('starts without SlackClient and falls back to logging', async () => {
    const moduleRef = await Test.createTestingModule({ providers: [NotifierService] }).compile();

    expect(moduleRef.get(NotifierService).notify('hi')).toBe('log: hi');
  });

  it('uses SlackClient when the application provides it', async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [SlackClient, NotifierService],
    }).compile();

    expect(moduleRef.get(NotifierService).notify('hi')).toBe('slack: hi');
  });
});

describe('Task 4b: @Optional() and a subclass with its own constructor', () => {
  it('LoudNotifierService starts without SlackClient', async () => {
    const moduleRef = await Test.createTestingModule({ providers: [LoudNotifierService] }).compile();

    expect(moduleRef.get(LoudNotifierService).notify('hi')).toBe('log: HI');
  });

  it('LoudNotifierService uses SlackClient when it is provided', async () => {
    const moduleRef = await Test.createTestingModule({
      providers: [SlackClient, LoudNotifierService],
    }).compile();

    expect(moduleRef.get(LoudNotifierService).notify('hi')).toBe('slack: HI');
  });
});
