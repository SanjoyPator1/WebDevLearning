import type { CanActivate } from '@nestjs/common';

// Not part of this exercise: every TraceGuard and the handlers write their name into this array,
// so the tests can read the order things ran in. `allow` makes a guard deny the request.
export const trace: string[] = [];

export class TraceGuard implements CanActivate {
  constructor(
    private readonly name: string,
    private readonly allow = true,
  ) {}

  canActivate(): boolean {
    trace.push(this.name);
    return this.allow;
  }
}
