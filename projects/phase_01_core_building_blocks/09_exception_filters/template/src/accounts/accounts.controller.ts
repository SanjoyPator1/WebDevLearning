import { Controller, Get } from '@nestjs/common';

// TODO(1.9) Task 1
// Nest's built-in exceptions (BadRequestException, NotFoundException, ConflictException, ...) are
// all HttpExceptions: throwing one is how a handler answers with an error status. Each handler
// below throws a placeholder. Replace it so the client gets exactly the response described.
// Look at the constructor arguments: a message (string or array of strings), and the options
// object, which in Nest 12 accepts `errorCode`.
//
//   GET /accounts/missing          404  { message: 'account 7 not found', error: 'Not Found', statusCode: 404 }
//   GET /accounts/weak-password    400  { message: 'password too short', error: 'Bad Request', statusCode: 400,
//                                         errorCode: 'WEAK_PASSWORD' }
//   GET /accounts/duplicate        409  { message: 'email already registered', error: 'Conflict', statusCode: 409,
//                                         errorCode: 'DUPLICATE_EMAIL' }
//   GET /accounts/fields           400  { message: ['name must not be empty', 'age must be positive'],
//                                         error: 'Bad Request', statusCode: 400 }
//   GET /accounts/custom           422  EXACTLY the body { code: 'E1', hint: 'try again' }, and nothing else
//                                       (use the generic HttpException, which takes a status code; look at
//                                       what happens to the body when you give it an object)
@Controller('accounts')
export class AccountsController {
  @Get('missing')
  missing(): never {
    throw new Error('TODO(1.9) Task 1: missing');
  }

  @Get('weak-password')
  weakPassword(): never {
    throw new Error('TODO(1.9) Task 1: weakPassword');
  }

  @Get('duplicate')
  duplicate(): never {
    throw new Error('TODO(1.9) Task 1: duplicate');
  }

  @Get('fields')
  fields(): never {
    throw new Error('TODO(1.9) Task 1: fields');
  }

  @Get('custom')
  custom(): never {
    throw new Error('TODO(1.9) Task 1: custom');
  }

  // Not part of the task: an unexpected failure. What reaches the client? (The guard test.)
  @Get('crash')
  crash(): never {
    throw new Error('database password is hunter2');
  }
}
