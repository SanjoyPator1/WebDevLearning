import { Body, Controller, Post } from '@nestjs/common';
import type { Person } from './person.schema.js';

// TODO(1.6) Task 7b
// A first look at validation pipes (the deep dive is topic 3.2). In Nest 12 a parameter decorator
// accepts a schema:  @Body({ schema: personSchema })  and a pipe that understands schemas.
// Wire it up:
//   1. attach personSchema to the @Body() parameter
//   2. bind the built-in StandardSchemaValidationPipe to this controller (as a class)
// A schema on a parameter does nothing by itself: the pipe is what reads it. The test shows
// what happens without the pipe.
@Controller('people')
export class PeopleController {
  @Post()
  create(@Body() person: Person): Person {
    return person;
  }
}
