export interface Person {
  name: string;
  age: number;
}

export interface Issue {
  message: string;
  path?: ReadonlyArray<string | number>;
}

// TODO(1.6) Task 7a
// A "Standard Schema" is not a library: it is any object that has a `~standard` property with a
// `validate` function. Zod, Valibot and ArkType all produce one, and Nest 12 can use any of them.
// Writing a tiny one by hand shows what the interface is. validate(value) returns EITHER
//   { value }     the (possibly transformed) result when the input is valid, OR
//   { issues }    a list of { message, path } when it is not.
//
// Make it accept an object { name, age } and
//   - name: a string with at least 2 characters AFTER trimming; the result has the trimmed name
//           issue: { message: 'must be at least 2 characters', path: ['name'] }
//   - age:  a whole number, zero or more
//           issue: { message: 'must be a non-negative integer', path: ['age'] }
//   - report EVERY problem at once, not just the first
//   - input that is not an object at all: one issue { message: 'expected an object' } (no path)
export const personSchema = {
  '~standard': {
    version: 1 as const,
    vendor: 'exercise',
    validate: (value: unknown): { value: Person } | { issues: Issue[] } => {
      throw new Error('TODO(1.6) Task 7a: personSchema');
    },
  },
};
