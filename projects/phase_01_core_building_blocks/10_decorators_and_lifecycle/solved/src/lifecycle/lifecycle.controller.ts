import {
  BadRequestException,
  Controller,
  Get,
  HttpCode,
  Param,
  UseFilters,
  UseGuards,
  UseInterceptors,
  UsePipes,
} from '@nestjs/common';
import {
  StatusGuard,
  StatusInterceptor,
  TraceFilter,
  TraceGuard,
  TraceInterceptor,
  TracePipe,
  trace,
} from './components.js';

// Not part of this exercise: one controller with a component of every kind at every scope, and four
// routes that end in four different ways. Read it, then predict the traces in predictions.ts.
// The global components (a middleware, a guard, an interceptor, a pipe and a filter) are registered in
// configure-lifecycle.ts, and a middleware for this controller in lifecycle.module.ts.
@Controller('life')
@UseGuards(new TraceGuard('controller'))
@UseInterceptors(new TraceInterceptor('controller'))
@UsePipes(new TracePipe('controller'))
export class LifecycleController {
  // Everything succeeds.
  @Get('ok/:id')
  @UseGuards(new TraceGuard('method'))
  @UseInterceptors(new TraceInterceptor('method'))
  @UsePipes(new TracePipe('method'))
  @UseFilters(new TraceFilter('method'))
  ok(@Param('id', new TracePipe('param')) id: string): string {
    trace.push('handler');
    return id;
  }

  // The method guard says no.
  @Get('denied/:id')
  @UseGuards(new TraceGuard('method', false))
  @UseInterceptors(new TraceInterceptor('method'))
  @UsePipes(new TracePipe('method'))
  @UseFilters(new TraceFilter('method'))
  denied(@Param('id', new TracePipe('param')) id: string): string {
    trace.push('handler');
    return id;
  }

  // The parameter pipe throws.
  @Get('pipefail/:id')
  @UseGuards(new TraceGuard('method'))
  @UseInterceptors(new TraceInterceptor('method'))
  @UsePipes(new TracePipe('method'))
  @UseFilters(new TraceFilter('method'))
  pipefail(@Param('id', new TracePipe('param', true)) id: string): string {
    trace.push('handler');
    return id;
  }

  // The handler throws.
  @Get('handlerfail/:id')
  @UseGuards(new TraceGuard('method'))
  @UseInterceptors(new TraceInterceptor('method'))
  @UsePipes(new TracePipe('method'))
  @UseFilters(new TraceFilter('method'))
  handlerfail(@Param('id', new TracePipe('param')) id: string): string {
    trace.push('handler');
    throw new BadRequestException(`handler failed for ${id}`);
  }

  // A route that sets a status code and records what the response looks like in a guard and in an interceptor.
  @Get('status')
  @HttpCode(202)
  @UseGuards(new StatusGuard())
  @UseInterceptors(new StatusInterceptor())
  status(): string {
    return 'status';
  }
}
