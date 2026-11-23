export interface Person {
  name: string;
  age: number;
}

export interface Issue {
  message: string;
  path?: ReadonlyArray<string | number>;
}

// Task 7a: a Standard Schema (standardschema.dev) is a convention, not a package: any object with a
// `~standard` property holding `version`, `vendor` and a `validate(value)` function. validate returns
// `{ value }` for valid input (the value may be transformed: here the name is trimmed) or
// `{ issues }`, a list of `{ message, path }`. It may also return a Promise.
// Zod, Valibot and ArkType all implement this, so Nest does not depend on any of them: it only
// calls `schema['~standard'].validate(value)`.
//
// Collecting every issue before returning is what makes the error message useful to a client.
export const personSchema = {
  '~standard': {
    version: 1 as const,
    vendor: 'exercise',
    validate: (value: unknown): { value: Person } | { issues: Issue[] } => {
      if (typeof value !== 'object' || value === null || Array.isArray(value)) {
        return { issues: [{ message: 'expected an object' }] };
      }
      const { name, age } = value as Record<string, unknown>;
      const issues: Issue[] = [];

      const trimmed = typeof name === 'string' ? name.trim() : '';
      if (trimmed.length < 2) {
        issues.push({ message: 'must be at least 2 characters', path: ['name'] });
      }
      if (typeof age !== 'number' || !Number.isInteger(age) || age < 0) {
        issues.push({ message: 'must be a non-negative integer', path: ['age'] });
      }

      return issues.length > 0 ? { issues } : { value: { name: trimmed, age: age as number } };
    },
  },
};
