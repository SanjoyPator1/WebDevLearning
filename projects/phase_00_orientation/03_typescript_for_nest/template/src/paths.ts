// Not part of this exercise: a path helper so you can focus on metadata.

/** joinPaths('cats', ':id') -> '/cats/:id', joinPaths('cats', '') -> '/cats', joinPaths('', '') -> '/' */
export function joinPaths(prefix: string, path: string): string {
  const parts = [prefix, path].map((part) => part.replace(/^\/+|\/+$/g, '')).filter(Boolean);
  return '/' + parts.join('/');
}
