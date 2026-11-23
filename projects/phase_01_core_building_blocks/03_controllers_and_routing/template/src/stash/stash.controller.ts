import { Body, Controller, Get, Param, Put } from '@nestjs/common';
import type { Response } from 'express';
import { ItemsService, type Item } from '../items/items.service.js';

// The routes are given. TODO(1.3) Task 4: take the response object with @Res, once with
// passthrough and once without. The two modes behave very differently.
@Controller('stash')
export class StashController {
  constructor(private readonly items: ItemsService) {}

  // TODO(1.3) Task 4a: PUT /stash/:id with body { "name": "..." } stores the item under that id
  // (ItemsService.upsert tells you whether it was created).
  //   created  -> status 201     already there -> status 200
  // Both set the response header "Location: /stash/<id>" and return the item as JSON.
  // Add a `res` parameter and set the status and the header on it, but let Nest send the
  // response: the handler still returns the item.
  @Put(':id')
  put(@Param('id') id: string, @Body('name') name: string): Item {
    throw new Error('TODO(1.3) Task 4a: put');
  }

  // TODO(1.3) Task 4b: GET /stash/:id/text sends the item as plain text "<id>:<name>".
  // An unknown id answers status 404 with the plain text "not found".
  // Here the handler owns the whole response: take `res` and send the text yourself.
  // The method returns nothing.
  @Get(':id/text')
  text(@Param('id') id: string): void {
    throw new Error('TODO(1.3) Task 4b: text');
  }
}
