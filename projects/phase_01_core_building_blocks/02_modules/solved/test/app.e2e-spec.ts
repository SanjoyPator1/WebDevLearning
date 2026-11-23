import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { AppModule } from '../src/app.module.js';
import { CounterService } from '../src/counter/counter.service.js';

describe('Task 7: AppModule wires everything together (e2e)', () => {
  let app: INestApplication;

  beforeEach(async () => {
    CounterService.created = 0;
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] }).compile();
    app = moduleRef.createNestApplication();
    await app.init();
  });

  afterEach(async () => {
    await app.close();
  });

  it('GET /greet/:name counts up across requests', async () => {
    await request(app.getHttpServer()).get('/greet/ada').expect(200).expect('Hello, ada! (#1)');
    await request(app.getHttpServer()).get('/greet/bob').expect(200).expect('Hello, bob! (#2)');
  });

  it('GET /report sees the same counter as the greeter', async () => {
    await request(app.getHttpServer()).get('/greet/ada').expect(200);
    await request(app.getHttpServer()).get('/report').expect(200).expect('greetings so far: 1');
  });

  it('the whole app has exactly one CounterService', () => {
    expect(CounterService.created).toBe(1);
  });
});
