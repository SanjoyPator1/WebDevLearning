import { Controller, Get } from '@nestjs/common';
import { Public } from './public.decorator.js';

// Not part of this exercise: routes that are private by default, public, public through their
// controller, and private again inside a public controller.
@Controller('shop')
export class ShopController {
  @Get('items')
  items(): string[] {
    return ['anvil', 'bellows'];
  }

  @Get('health')
  @Public(true)
  health(): string {
    return 'ok';
  }
}

@Controller('docs')
@Public(true)
export class DocsController {
  @Get()
  index(): string {
    return 'docs';
  }

  @Get('internal')
  @Public(false)
  internal(): string {
    return 'internal docs';
  }
}
