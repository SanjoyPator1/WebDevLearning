import type { Request } from 'express';

// Not part of this exercise: the user that the guards attach to the request, and the roles each name has.
export interface User {
  name: string;
  roles: string[];
}

export type AuthedRequest = Request & { user?: User };

export function userNamed(name: string): User {
  const roles: Record<string, string[]> = { ada: ['admin'], eve: ['editor'] };
  return { name, roles: roles[name] ?? [] };
}
