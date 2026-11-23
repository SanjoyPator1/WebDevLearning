import {
  BadRequestException,
  Controller,
  Get,
  HttpException,
  NotFoundException,
  UseFilters,
} from '@nestjs/common';
import { ErrorEnvelopeFilter } from './error-envelope.filter.js';

// Not part of this exercise: routes that throw different kinds of exceptions, behind the filter of Task 2
// (bound once on the class).
@Controller('shapes')
@UseFilters(ErrorEnvelopeFilter)
export class ShapesController {
  @Get('coded')
  coded(): never {
    throw new BadRequestException('too short', { errorCode: 'WEAK' });
  }

  @Get('list')
  list(): never {
    throw new BadRequestException(['a must be set', 'b must be set']);
  }

  @Get('plain404')
  plain404(): never {
    throw new NotFoundException();
  }

  @Get('object')
  object(): never {
    throw new HttpException({ code: 'E1' }, 422);
  }

  @Get('crash')
  crash(): never {
    throw new Error('not an HttpException');
  }
}
