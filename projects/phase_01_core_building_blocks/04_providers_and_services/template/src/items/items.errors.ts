// Not part of this exercise: domain errors. They say what went wrong in the language of the
// business and know nothing about HTTP. Mapping them to status codes is topic 1.9.
export class InvalidItemError extends Error {
  constructor(message = 'item name must not be empty') {
    super(message);
    this.name = 'InvalidItemError';
  }
}

export class DuplicateItemError extends Error {
  constructor(name: string) {
    super(`item "${name}" already exists`);
    this.name = 'DuplicateItemError';
  }
}

export class ItemNotFoundError extends Error {
  constructor(id: number) {
    super(`item ${id} not found`);
    this.name = 'ItemNotFoundError';
  }
}
