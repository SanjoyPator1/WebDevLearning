import { BadRequestException, Controller, Get } from '@nestjs/common';

// TODO(1.9) Task 5b
// Bind NamedFilter (instances: `new NamedFilter('controller')`) so that these routes are handled by:
//   GET /scopes/one    the 'method' filter       (filters at global, controller AND method level)
//   GET /scopes/two    the 'controller' filter   (global and controller level only)
//   GET /scopes/four   the 'second' filter       (two filters on the route: 'first' then 'second')
//   GET /plain         the 'global' filter       (PlainController below, which you do not change)
// Every NamedFilter catches everything, so this is a test of PRECEDENCE: unlike guards, pipes and
// interceptors, only ONE filter handles an exception. Do not change the method bodies.
@Controller('scopes')
export class ScopesController {
  @Get('one')
  one(): never {
    throw new BadRequestException();
  }

  @Get('two')
  two(): never {
    throw new BadRequestException();
  }

  @Get('four')
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
