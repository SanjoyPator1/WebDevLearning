import { Injectable } from '@nestjs/common';

// Not part of this exercise: a provider (topic 1.4) that the guard of Task 2 needs. verify() is
// asynchronous, like a database or identity-provider lookup would be.
@Injectable()
export class TokenService {
  private readonly tokens = new Map<string, string>([
    ['t-ada', 'ada'],
    ['t-bob', 'bob'],
  ]);

  /** The user name the token belongs to, or null when the token is unknown. */
  async verify(token: string): Promise<string | null> {
    await new Promise((resolve) => setTimeout(resolve, 5));
    return this.tokens.get(token) ?? null;
  }
}
