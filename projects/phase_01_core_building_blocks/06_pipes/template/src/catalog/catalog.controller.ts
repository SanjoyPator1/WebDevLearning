import { Controller, Get, Param } from '@nestjs/common';
import { SkuExistsPipe } from './sku-exists.pipe.js';

// Not part of this exercise: the pipe is already bound, as a class.
@Controller('catalog')
export class CatalogController {
  @Get(':sku')
  get(@Param('sku', SkuExistsPipe) product: string): { product: string } {
    return { product };
  }
}
