import {
  Controller,
  DefaultValuePipe,
  Get,
  Param,
  ParseBoolPipe,
  ParseDatePipe,
  ParseEnumPipe,
  ParseUUIDPipe,
  Query,
} from '@nestjs/common';

export enum Color {
  Red = 'red',
  Blue = 'blue',
}

// Task 2: one built-in pipe per kind of value.
//   ParseUUIDPipe({ version: '4' })  a version 4 UUID, the string unchanged. Without the option
//                                    any version passes.
//   ParseEnumPipe(Color)             matches the enum VALUES ('red'), case-sensitively, not the
//                                    keys ('Red'). A missing value is rejected unless the pipe
//                                    is given `{ optional: true }` (every parse pipe has it).
//   DefaultValuePipe(false) then ParseBoolPipe
//                                    ParseBoolPipe accepts only "true" and "false" (and real
//                                    booleans, which is why the default can be the boolean false).
//                                    "1", "yes" and "TRUE" are rejected.
//   ParseDatePipe({ optional: true }) turns an ISO string into a Date. optional lets a missing
//                                    value through as undefined; an empty string or garbage is
//                                    still a 400.
// Each throws its own message, e.g. "Validation failed (uuid v 4 is expected)".
@Controller('filters')
export class FiltersController {
  @Get(':uuid')
  find(
    @Param('uuid', new ParseUUIDPipe({ version: '4' })) uuid: string,
    @Query('color', new ParseEnumPipe(Color)) color: Color,
    @Query('archived', new DefaultValuePipe(false), ParseBoolPipe) archived: boolean,
    @Query('since', new ParseDatePipe({ optional: true })) since?: Date,
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
