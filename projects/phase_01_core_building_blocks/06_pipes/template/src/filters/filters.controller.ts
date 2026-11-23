import { Controller, Get, Param, Query } from '@nestjs/common';

export enum Color {
  Red = 'red',
  Blue = 'blue',
}

// TODO(1.6) Task 2
// More built-in pipes. Make the handler receive exactly these values (a bad value answers 400):
//   uuid      a UUID of version 4 only (a version 1 UUID is rejected)
//   color     one of the Color VALUES; required
//   archived  a real boolean, "true" or "false"; when missing it is false
//   since     a real Date; optional (missing stays undefined)
// Do not change the method body.
@Controller('filters')
export class FiltersController {
  @Get(':uuid')
  find(
    @Param('uuid') uuid: string,
    @Query('color') color: Color,
    @Query('archived') archived: boolean,
    @Query('since') since?: Date,
  ): { uuid: string; color: Color; archived: boolean; archivedType: string; since: string | null; sinceIsDate: boolean } {
    return {
      uuid,
      color,
      archived,
      archivedType: typeof archived,
      since: since?.toISOString() ?? null,
      sinceIsDate: since instanceof Date,
    };
  }
}
