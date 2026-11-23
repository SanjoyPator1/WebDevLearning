import { Controller, Get } from '@nestjs/common';

// Not part of this exercise: a controller is topic 1.3. It only gives the app two routes to talk to.
@Controller()
export class HealthController {
  @Get('health')
  health() {
    return { status: 'ok' };
  }

  @Get('version')
  version() {
    return { version: '1' };
  }
}
