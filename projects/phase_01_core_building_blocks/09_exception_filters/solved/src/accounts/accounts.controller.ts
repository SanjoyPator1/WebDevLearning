import {
  BadRequestException,
  ConflictException,
  Controller,
  Get,
  HttpException,
  NotFoundException,
} from '@nestjs/common';

// Task 1: every built-in exception is an HttpException with a fixed status. The constructor decides the
// response body (measured, Nest 12.5.1):
//   new X()                       { message: 'Bad Request', statusCode }                  (no `error` field)
//   new X('text')                 { message: 'text', error: 'Bad Request', statusCode }
//   new X(['a', 'b'])             { message: ['a', 'b'], error: ..., statusCode }
//   new X('text', { errorCode })  the same plus `errorCode` (new in v12)
//   new X({ any: 'object' })      EXACTLY that object: Nest adds nothing, so you own the whole shape
//   new HttpException(body, 422)  the generic form, for a status without its own class
// `errorCode` is added only for the string, array and empty forms; with an object body (even with the
// option) it is only stored on the exception (`exception.errorCode`) and NOT written to the body, because
// an object body is sent as it is. `cause` (another option) is for your logs and never reaches the client.
// Throwing a plain Error instead is a generic 500 that hides the message and is logged (see `crash`).
@Controller('accounts')
export class AccountsController {
  @Get('missing')
  missing(): never {
    throw new NotFoundException('account 7 not found');
  }

  @Get('weak-password')
  weakPassword(): never {
    throw new BadRequestException('password too short', { errorCode: 'WEAK_PASSWORD' });
  }

  @Get('duplicate')
  duplicate(): never {
    throw new ConflictException('email already registered', { errorCode: 'DUPLICATE_EMAIL' });
  }

  @Get('fields')
  fields(): never {
    throw new BadRequestException(['name must not be empty', 'age must be positive']);
  }

  @Get('custom')
  custom(): never {
    throw new HttpException({ code: 'E1', hint: 'try again' }, 422);
  }

  // Not part of the task: an unexpected failure. What reaches the client? (The guard test.)
  @Get('crash')
  crash(): never {
    throw new Error('database password is hunter2');
  }
}
