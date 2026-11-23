import type { PipeTransform } from '@nestjs/common';

// TODO(1.6) Task 6
// A pipe that needs a provider. Pipes can be injectable classes, like any provider (topic 1.4).
//   - mark it injectable and ask for CatalogService in the constructor
//   - transform(sku): look the sku up with CatalogService.find()
//       found    -> return the PRODUCT NAME (the handler gets the name, not the sku)
//       unknown  -> throw a BadRequestException with the message  unknown sku "<sku>"
// This only works when the pipe is bound as a CLASS (@Param('sku', SkuExistsPipe)): Nest builds
// the instance and injects it. An instance you create with `new` has no injection.
export class SkuExistsPipe implements PipeTransform<string, string> {
  transform(sku: string): string {
    throw new Error('TODO(1.6) Task 6: SkuExistsPipe');
  }
}
