import { Body, Controller, Post } from '@nestjs/common';
import request from 'supertest';
import { PeopleController } from '../src/people/people.controller.js';
import { personSchema, type Person } from '../src/people/person.schema.js';
import { createApp } from './helpers.js';

// A controller written only for the guard test: the schema is attached, but NO pipe is bound.
@Controller('unprotected')
class UnprotectedController {
  @Post()
  create(@Body({ schema: personSchema }) person: Person): Person {
    return person;
  }
}

describe('Task 7a: a hand-written Standard Schema', () => {
  it('returns the cleaned value for valid input', async () => {
    const result = await personSchema['~standard'].validate({ name: '  ada ', age: 30 });

    expect(result).toEqual({ value: { name: 'ada', age: 30 } });
  });

  it('reports every issue at once, with a path', async () => {
    const result = await personSchema['~standard'].validate({ name: 'a', age: -1 });

    expect(result).toEqual({
      issues: [
        { message: 'must be at least 2 characters', path: ['name'] },
        { message: 'must be a non-negative integer', path: ['age'] },
      ],
    });
  });

  it('judges the name after trimming, and wants age to be a number', async () => {
    expect(await personSchema['~standard'].validate({ name: '  a  ', age: 1 })).toHaveProperty('issues');
    expect(await personSchema['~standard'].validate({ name: 'ada', age: '30' })).toHaveProperty('issues');
    expect(await personSchema['~standard'].validate({ name: 'ada', age: 1.5 })).toHaveProperty('issues');
  });

  it('input that is not an object is one issue without a path', async () => {
    for (const bad of [undefined, null, 'text', 5, []]) {
      expect(await personSchema['~standard'].validate(bad)).toEqual({ issues: [{ message: 'expected an object' }] });
    }
  });
});

describe('Task 7b: StandardSchemaValidationPipe', () => {
  it('passes valid input through and uses the schema OUTPUT (the name arrives trimmed)', async () => {
    const { app } = await createApp([PeopleController]);

    const res = await request(app.getHttpServer()).post('/people').send({ name: '  ada ', age: 30 }).expect(201);

    expect(res.body).toEqual({ name: 'ada', age: 30 });
    await app.close();
  });

  it('answers 400 with one message per issue, prefixed by its path', async () => {
    const { app } = await createApp([PeopleController]);

    const res = await request(app.getHttpServer()).post('/people').send({ name: 'a', age: -1 }).expect(400);

    expect(res.body).toEqual({
      message: ['name: must be at least 2 characters', 'age: must be a non-negative integer'],
      error: 'Bad Request',
      statusCode: 400,
    });
    await app.close();
  });

  it('a request without a body is rejected too', async () => {
    const { app } = await createApp([PeopleController]);

    const res = await request(app.getHttpServer()).post('/people').expect(400);

    expect(res.body.message).toEqual(['expected an object']);
    await app.close();
  });

  it('guard: a schema on a parameter is ignored when no schema pipe is bound', async () => {
    const { app } = await createApp([UnprotectedController]);

    const res = await request(app.getHttpServer()).post('/unprotected').send({ name: 'a', age: -1 }).expect(201);

    expect(res.body).toEqual({ name: 'a', age: -1 });
    await app.close();
  });
});
