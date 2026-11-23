import { Controller, Delete, Get, Param, UseGuards } from '@nestjs/common';
import { Roles } from './roles.decorator.js';
import { RolesGuard } from './roles.guard.js';

// Not part of this exercise: the decorator and the guard are bound here; Task 3 is writing them.
@Controller('reports')
@UseGuards(RolesGuard)
@Roles(['viewer', 'admin'])
export class ReportsController {
  // Inherits the controller's roles: viewer or admin.
  @Get()
  list(): string {
    return 'reports';
  }

  // The method's roles REPLACE the controller's: admin only.
  @Delete(':id')
  @Roles(['admin'])
  remove(@Param('id') id: string): string {
    return `deleted ${id}`;
  }

  // An empty list replaces the controller's roles too: nobody in particular is required.
  @Get('open')
  @Roles([])
  open(): string {
    return 'open';
  }
}
