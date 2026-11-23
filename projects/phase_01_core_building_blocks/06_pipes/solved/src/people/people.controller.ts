import { Body, Controller, Post, StandardSchemaValidationPipe, UsePipes } from '@nestjs/common';
import { personSchema, type Person } from './person.schema.js';

// Task 7b: two halves.
//   @Body({ schema: personSchema })   stores the schema in the parameter's metadata (ArgumentMetadata.schema)
//   StandardSchemaValidationPipe      reads metadata.schema and runs it
// The decorator alone does nothing: without the pipe the schema is ignored and the body arrives
// unchecked (the guard test in people.spec.ts). The pipe, in turn, ignores parameters that carry
// no schema, so it can be bound once, even globally, and only the parameters that opt in are checked.
//
// What the pipe does with the result: invalid input throws a 400 whose `message` is an ARRAY, one
// entry per issue, formatted "path: message" (for example "name: must be at least 2 characters").
// Valid input is replaced by the schema's OUTPUT (the name arrives trimmed), because the pipe's
// `transform` option defaults to true. Options: errorHttpStatusCode, exceptionFactory, transform.
//
// This is the first look; class-validator DTOs (`ValidationPipe`), real libraries such as Zod, and
// choosing between them are topic 3.2.
@Controller('people')
@UsePipes(StandardSchemaValidationPipe)
export class PeopleController {
  @Post()
  create(@Body({ schema: personSchema }) person: Person): Person {
    return person;
  }
}
