import { Body, Controller, Get, Param, Patch, Post, Query } from '@nestjs/common';
import { ItemsService, type Item } from './items.service.js';
import { UpdateItemDto } from './update-item.dto.js';

// Task 1: @Controller('items') marks the class as a controller (without it Nest throws
// "An invalid controller has been detected" at startup) and stores the prefix "items",
// which is joined in front of every route path below.
@Controller('items')
export class ItemsController {
  constructor(private readonly items: ItemsService) {}

  // @Query('name') reads one key of the parsed query string. A query value is a string (or an
  // array of strings when the key repeats), so `limit` is converted by hand. Pipes (1.6) do it
  // declaratively.
  @Get()
  list(@Query('search') search?: string, @Query('limit') limit?: string): Item[] {
    return this.items.findAll(search, limit === undefined ? undefined : Number(limit));
  }

  // The route parameter is always a string, even though the URL says /items/2.
  // An unknown id returns undefined, which Nest sends as an empty 200. Turning that into a
  // 404 is the job of HttpException and exception filters (1.9).
  @Get(':id')
  findOne(@Param('id') id: string): Item | undefined {
    return this.items.findOne(Number(id));
  }

  // @Body('name') reads one property of the parsed JSON body. A POST answers 201 by default.
  @Post()
  create(@Body('name') name: string): Item {
    return this.items.create(name);
  }

  // Task 8: @Body() hands over the whole parsed body, and the parameter's type is the DTO class.
  // TypeScript emits that class as design:paramtypes, which is how pipes (1.6, 3.2) later find
  // what to validate against. On its own the class changes nothing: the value that arrives is
  // still a plain object, not an UpdateItemDto instance (see the last test in dto.spec.ts).
  @Patch(':id')
  update(@Param('id') id: string, @Body() dto: UpdateItemDto): Item | undefined {
    return this.items.rename(Number(id), dto.name);
  }
}
