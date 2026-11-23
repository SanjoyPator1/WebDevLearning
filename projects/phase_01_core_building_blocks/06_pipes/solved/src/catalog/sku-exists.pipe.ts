import { BadRequestException, Injectable, type PipeTransform } from '@nestjs/common';
import { CatalogService } from './catalog.service.js';

// Task 6: a pipe is a provider-like class. Bound as a CLASS (`@Param('sku', SkuExistsPipe)`), Nest
// builds it once in the module of the controller and injects its constructor dependencies, and every
// use of the pipe in that module shares the one instance (so it sees the same CatalogService as
// everything else). Bound as an instance (`new SkuExistsPipe(...)`) you would have to pass the
// dependency yourself.
//
// A pipe that turns an identifier into the thing it names is a common use: the handler receives the
// product name, not the raw sku. Whether "unknown" is a 400 (a bad parameter) or a 404 (a missing
// resource) is a design decision; a 404 would use NotFoundException (1.9). A pipe that reaches a
// database like this adds a query to every request that uses it: weigh that against doing the
// lookup in the service.
@Injectable()
export class SkuExistsPipe implements PipeTransform<string, string> {
  constructor(private readonly catalog: CatalogService) {}

  transform(sku: string): string {
    const name = this.catalog.find(sku);
    if (name === undefined) {
      throw new BadRequestException(`unknown sku "${sku}"`);
    }
    return name;
  }
}
