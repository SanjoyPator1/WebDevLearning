import { Body, Controller, Get, Param, Put, Res } from '@nestjs/common';
import type { Response } from 'express';
import { ItemsService, type Item } from '../items/items.service.js';

@Controller('stash')
export class StashController {
  constructor(private readonly items: ItemsService) {}

  // 4a: { passthrough: true } gives you the response object to set the status and headers,
  // but Nest still sends the response from the returned value. Interceptors and serialization
  // (1.8, 3.3) keep working. This is the form to use when you need `res` at all.
  @Put(':id')
  put(
    @Param('id') id: string,
    @Body('name') name: string,
    @Res({ passthrough: true }) res: Response,
  ): Item {
    const { item, created } = this.items.upsert(Number(id), name);
    res.status(created ? 201 : 200);
    res.setHeader('Location', `/stash/${item.id}`);
    return item;
  }

  // 4b: a plain @Res() switches Nest's response handling off for this handler. Whatever the
  // method returns is ignored, and if you never call res.send/end/json the request hangs
  // until the client times out (measured in 12.5.1). Interceptors cannot map the result and
  // the handler is harder to test. Prefer 4a, or no @Res at all.
  @Get(':id/text')
  text(@Param('id') id: string, @Res() res: Response): void {
    const item = this.items.findOne(Number(id));
    res.type('text/plain');
    if (!item) {
      res.status(404).send('not found');
      return;
    }
    res.send(`${item.id}:${item.name}`);
  }
}
