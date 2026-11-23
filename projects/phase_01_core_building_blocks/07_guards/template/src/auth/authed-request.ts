import type { Request } from 'express';

// Not part of this exercise: an Express request that the guard of Task 2 may have given a `user`.
export type AuthedRequest = Request & { user?: { name: string } };
