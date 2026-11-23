import { BadRequestException, Controller, Get, UseFilters } from '@nestjs/common';
import { NamedFilter } from './named.filter.js';

// Task 5b: filters are bound like guards, pipes and interceptors, but they work differently. Those
// run EVERY bound component in a chain; for an exception Nest picks ONE filter and only that one runs:
//   - the narrowest scope wins: method, then controller, then global (measured). The list of filters is
//     reversed before matching (`router-exception-filters.js`), which is also why the last of
//     @UseFilters(a, b) is tried first.
//   - inside one @UseFilters(a, b) the LAST one wins (measured: 'second' handled it)
//   - within a scope a filter only qualifies if its @Catch matches the exception (`instanceof`); the
//     first qualifying one handles it. If none qualifies, Nest's default handling answers.
// Consequence: a global catch-all filter does NOT see an exception that a narrower filter caught, which
// is why a logging filter belongs at the narrowest scope that must not be skipped, or must delegate.
// A filter cannot pass the exception on to the next filter; to fall back to the default behaviour,
// extend BaseExceptionFilter and call super.catch() (Task 4).
@Controller('scopes')
@UseFilters(new NamedFilter('controller'))
export class ScopesController {
  @Get('one')
  @UseFilters(new NamedFilter('method'))
  one(): never {
    throw new BadRequestException();
  }

  @Get('two')
  two(): never {
    throw new BadRequestException();
  }

  @Get('four')
  @UseFilters(new NamedFilter('first'), new NamedFilter('second'))
  four(): never {
    throw new BadRequestException();
  }
}

// Not part of the task: a controller with no filter of its own.
@Controller('plain')
export class PlainController {
  @Get()
  plain(): never {
    throw new BadRequestException();
  }
}
