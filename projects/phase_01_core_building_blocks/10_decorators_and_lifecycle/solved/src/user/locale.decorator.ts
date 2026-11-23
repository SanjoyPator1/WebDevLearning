import { type ExecutionContext, createParamDecorator } from '@nestjs/common';
import type { Request } from 'express';

// Task 2: a decorator with no data. The factory's first parameter is unused, so it is `unknown`.
// Parsing: take the text before the first comma (the first tag, 'fr-CH;q=0.9' or 'EN-us'), drop the
// quality and the region, and lower-case it. Anything missing or empty falls back to 'en'.
// Putting a parsing rule like this in a decorator keeps it in one tested place instead of repeating
// `req.headers['accept-language']?.split(...)` in handlers. (Real content negotiation, with quality
// values and a list of supported languages, belongs in a service or in an i18n library: 7.6.)
export const Locale = createParamDecorator((_data: unknown, context: ExecutionContext): string => {
  const header = context.switchToHttp().getRequest<Request>().headers['accept-language'];
  const first = typeof header === 'string' ? header.split(',')[0]?.split(';')[0]?.split('-')[0]?.trim() : undefined;
  return first ? first.toLowerCase() : 'en';
});
