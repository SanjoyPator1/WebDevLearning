// Not part of this exercise: a helper. It is a pure function with no state and no
// dependencies, so it is not a provider: nothing needs to inject it, you just import it.
export function normalizeName(raw: string): string {
  return raw.trim().toLowerCase();
}
