import { Injectable } from '@nestjs/common';

// Not part of this exercise: counts how many times the handler really ran.
@Injectable()
export class SecuredService {
  calls = 0;

  hit(): number {
    return ++this.calls;
  }
}
