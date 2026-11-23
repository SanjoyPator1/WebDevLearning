// Not part of this exercise: domain errors. They describe what went wrong in the language of the
// business and know nothing about HTTP: this is the point of having them (see topic 1.4). Mapping them to
// statuses is the job of an exception filter (Task 3), at the edge of the application.
export abstract class DomainError extends Error {
  abstract readonly code: string;

  constructor(message: string) {
    super(message);
    this.name = this.constructor.name;
  }
}

export class OutOfStockError extends DomainError {
  readonly code = 'OUT_OF_STOCK';
  constructor(sku: string) {
    super(`${sku} is out of stock`);
  }
}

export class InvalidQuantityError extends DomainError {
  readonly code = 'INVALID_QUANTITY';
  constructor(quantity: number) {
    super(`quantity ${quantity} is not allowed`);
  }
}

export class UnknownProductError extends DomainError {
  readonly code = 'UNKNOWN_PRODUCT';
  constructor(sku: string) {
    super(`no product ${sku}`);
  }
}

export class DiscontinuedError extends DomainError {
  readonly code = 'DISCONTINUED';
  constructor(sku: string) {
    super(`${sku} is discontinued`);
  }
}
