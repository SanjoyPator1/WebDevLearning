import 'reflect-metadata';
import { describe, expect, it } from 'vitest';
import { Container } from '../src/container.js';
import { Inject, Injectable } from '../src/decorators.js';
import {
  CircularDependencyError,
  NotInjectableError,
  UnknownProviderError,
  UnresolvableDependencyError,
} from '../src/errors.js';
import { DESIGN_PARAMTYPES } from '../src/keys.js';

// Fixture classes are declared INSIDE each test (see decorators.test.ts for why).

describe('Task 3: register and registerValue', () => {
  it('accepts several @Injectable classes at once', () => {
    @Injectable()
    class A {}
    @Injectable()
    class B {}

    expect(() => new Container().register(A, B)).not.toThrow();
  });

  it('rejects a class without @Injectable()', () => {
    class Plain {}

    expect(() => new Container().register(Plain)).toThrow(NotInjectableError);
    expect(() => new Container().register(Plain)).toThrow('Plain is not decorated with @Injectable()');
  });

  it('does not build anything yet', () => {
    let built = 0;
    @Injectable()
    class Service {
      constructor() {
        built++;
      }
    }

    new Container().register(Service);

    expect(built).toBe(0);
  });
});

describe('Task 4: resolving classes through design:paramtypes', () => {
  it('builds a class without dependencies', () => {
    @Injectable()
    class Plain {}
    const container = new Container();
    container.register(Plain);

    expect(container.resolve(Plain)).toBeInstanceOf(Plain);
  });

  it('injects a dependency chosen only by the constructor parameter type', () => {
    @Injectable()
    class Repo {}
    @Injectable()
    class Service {
      constructor(readonly repo: Repo) {}
    }
    const container = new Container();
    container.register(Service, Repo);

    const service = container.resolve(Service);

    expect(service.repo).toBeInstanceOf(Repo);
  });

  it('resolves a chain of dependencies, whatever the registration order', () => {
    @Injectable()
    class Config {}
    @Injectable()
    class Db {
      constructor(readonly config: Config) {}
    }
    @Injectable()
    class Repo {
      constructor(readonly db: Db) {}
    }
    @Injectable()
    class Service {
      constructor(readonly repo: Repo, readonly config: Config) {}
    }
    const container = new Container();
    container.register(Service, Repo, Db, Config);

    const service = container.resolve(Service);

    expect(service.repo.db.config).toBeInstanceOf(Config);
    expect(service.config).toBe(service.repo.db.config);
  });

  it('passes the arguments in parameter order', () => {
    @Injectable()
    class First {}
    @Injectable()
    class Second {}
    @Injectable()
    class Both {
      constructor(readonly first: First, readonly second: Second) {}
    }
    const container = new Container();
    container.register(Both, First, Second);

    const both = container.resolve(Both);

    expect(both.first).toBeInstanceOf(First);
    expect(both.second).toBeInstanceOf(Second);
  });
});

describe('Task 5: singletons', () => {
  it('returns the same instance every time', () => {
    @Injectable()
    class Service {}
    const container = new Container();
    container.register(Service);

    expect(container.resolve(Service)).toBe(container.resolve(Service));
  });

  it('builds a class once, however many consumers need it', () => {
    let built = 0;
    @Injectable()
    class Shared {
      constructor() {
        built++;
      }
    }
    @Injectable()
    class A {
      constructor(readonly shared: Shared) {}
    }
    @Injectable()
    class B {
      constructor(readonly shared: Shared) {}
    }
    const container = new Container();
    container.register(A, B, Shared);

    const a = container.resolve(A);
    const b = container.resolve(B);

    expect(a.shared).toBe(b.shared);
    expect(built).toBe(1);
  });

  it('keeps separate containers independent', () => {
    @Injectable()
    class Service {}
    const one = new Container();
    const two = new Container();
    one.register(Service);
    two.register(Service);

    expect(one.resolve(Service)).not.toBe(two.resolve(Service));
  });
});

describe('Task 6: @Inject tokens and registered values', () => {
  it('injects a value registered under a string token', () => {
    @Injectable()
    class Client {
      constructor(@Inject('API_URL') readonly url: string) {}
    }
    const container = new Container();
    container.register(Client);
    container.registerValue('API_URL', 'https://example.test');

    expect(container.resolve(Client).url).toBe('https://example.test');
  });

  it('injects a value registered under a symbol token', () => {
    const CONFIG = Symbol('CONFIG');
    @Injectable()
    class Client {
      constructor(@Inject(CONFIG) readonly config: { retries: number }) {}
    }
    const container = new Container();
    container.register(Client);
    container.registerValue(CONFIG, { retries: 3 });

    expect(container.resolve(Client).config).toEqual({ retries: 3 });
  });

  it('lets a token replace the parameter type, which is how an interface gets injected', () => {
    interface Logger {
      log(message: string): void;
    }
    const LOGGER = Symbol('LOGGER');
    const logger: Logger = { log: () => {} };
    @Injectable()
    class Service {
      // The type says Logger, which the compiler emits as Object. The token says LOGGER.
      constructor(@Inject(LOGGER) readonly logger: Logger) {}
    }
    const container = new Container();
    container.register(Service);
    container.registerValue(LOGGER, logger);

    expect(container.resolve(Service).logger).toBe(logger);
  });

  it('mixes class parameters and token parameters in one constructor', () => {
    @Injectable()
    class Repo {}
    @Injectable()
    class Service {
      constructor(readonly repo: Repo, @Inject('TABLE') readonly table: string) {}
    }
    const container = new Container();
    container.register(Service, Repo);
    container.registerValue('TABLE', 'cats');

    const service = container.resolve(Service);

    expect(service.repo).toBeInstanceOf(Repo);
    expect(service.table).toBe('cats');
  });

  it('returns a registered value as it is', () => {
    const container = new Container();
    const value = { a: 1 };
    container.registerValue('VALUE', value);

    expect(container.resolve('VALUE')).toBe(value);
  });
});

describe('Task 7: errors for things that cannot be resolved', () => {
  it('throws UnknownProviderError for a token that was never registered', () => {
    @Injectable()
    class Service {}
    const container = new Container();

    expect(() => container.resolve(Service)).toThrow(UnknownProviderError);
    expect(() => container.resolve(Service)).toThrow('No provider found for Service');
    expect(() => container.resolve('NOPE')).toThrow('No provider found for NOPE');
  });

  it('names the consumer, the parameter list and the missing argument', () => {
    class Missing {}
    @Injectable()
    class Dep {}
    @Injectable()
    class Consumer {
      constructor(readonly missing: Missing, readonly dep: Dep) {}
    }
    const container = new Container();
    container.register(Consumer, Dep);

    expect(() => container.resolve(Consumer)).toThrow(UnresolvableDependencyError);
    expect(() => container.resolve(Consumer)).toThrow(
      "Can't resolve dependencies of Consumer (?, Dep). Please make sure that the argument Missing at index [0] is registered.",
    );
  });

  it('reports the FIRST parameter that cannot be satisfied', () => {
    class MissingA {}
    class MissingB {}
    @Injectable()
    class Dep {}
    @Injectable()
    class Consumer {
      constructor(readonly dep: Dep, readonly a: MissingA, readonly b: MissingB) {}
    }
    const container = new Container();
    container.register(Consumer, Dep);

    expect(() => container.resolve(Consumer)).toThrow(
      "Can't resolve dependencies of Consumer (Dep, ?, MissingB). Please make sure that the argument MissingA at index [1] is registered.",
    );
  });

  it('shows Object for an interface-typed parameter, because the type does not exist at runtime', () => {
    interface Logger {
      log(message: string): void;
    }
    @Injectable()
    class Service {
      constructor(readonly logger: Logger) {}
    }
    const container = new Container();
    container.register(Service);

    expect(() => container.resolve(Service)).toThrow(
      "Can't resolve dependencies of Service (?). Please make sure that the argument Object at index [0] is registered.",
    );
  });

  it('reports a missing token dependency by its token', () => {
    @Injectable()
    class Client {
      constructor(@Inject('API_URL') readonly url: string) {}
    }
    const container = new Container();
    container.register(Client);

    expect(() => container.resolve(Client)).toThrow(
      "Can't resolve dependencies of Client (?). Please make sure that the argument API_URL at index [0] is registered.",
    );
  });

  it('blames the consumer that is missing something, not the one at the top', () => {
    class Missing {}
    @Injectable()
    class Inner {
      constructor(readonly missing: Missing) {}
    }
    @Injectable()
    class Outer {
      constructor(readonly inner: Inner) {}
    }
    const container = new Container();
    container.register(Outer, Inner);

    expect(() => container.resolve(Outer)).toThrow("Can't resolve dependencies of Inner (?).");
  });

  it('treats an undefined parameter type as unresolvable (what a circular import leaves behind)', () => {
    @Injectable()
    class Service {
      constructor(readonly dep: object) {}
    }
    // Simulate the metadata a circular import produces: the class was undefined when it was read.
    Reflect.defineMetadata(DESIGN_PARAMTYPES, [undefined], Service);
    const container = new Container();
    container.register(Service);

    expect(() => container.resolve(Service)).toThrow(
      "Can't resolve dependencies of Service (?). Please make sure that the argument undefined at index [0] is registered.",
    );
  });
});

describe('Task 8: circular dependencies', () => {
  // In real code a cycle between classes in one file fails earlier: the second class is still in
  // its temporal dead zone when the first one's metadata is evaluated (see the notes). The
  // container still has to detect cycles, so these tests write the metadata by hand.
  function link(consumer: Function, dependencies: Function[]): void {
    Reflect.defineMetadata(DESIGN_PARAMTYPES, dependencies, consumer);
  }

  it('detects a two-class cycle and shows it', () => {
    @Injectable()
    class A {}
    @Injectable()
    class B {}
    link(A, [B]);
    link(B, [A]);
    const container = new Container();
    container.register(A, B);

    expect(() => container.resolve(A)).toThrow(CircularDependencyError);
    expect(() => container.resolve(A)).toThrow('Circular dependency detected: A -> B -> A');
  });

  it('detects a class that depends on itself', () => {
    @Injectable()
    class Self {}
    link(Self, [Self]);
    const container = new Container();
    container.register(Self);

    expect(() => container.resolve(Self)).toThrow('Circular dependency detected: Self -> Self');
  });

  it('detects a cycle that does not include the class you asked for, and shows only the cycle', () => {
    @Injectable()
    class Entry {}
    @Injectable()
    class A {}
    @Injectable()
    class B {}
    @Injectable()
    class C {}
    link(Entry, [A]);
    link(A, [B]);
    link(B, [C]);
    link(C, [A]);
    const container = new Container();
    container.register(Entry, A, B, C);

    expect(() => container.resolve(Entry)).toThrow('Circular dependency detected: A -> B -> C -> A');
  });

  it('exposes the cycle as data', () => {
    @Injectable()
    class A {}
    @Injectable()
    class B {}
    link(A, [B]);
    link(B, [A]);
    const container = new Container();
    container.register(A, B);

    try {
      container.resolve(A);
      expect.unreachable('resolve should have thrown');
    } catch (error) {
      expect(error).toBeInstanceOf(CircularDependencyError);
      expect((error as CircularDependencyError).cycle).toEqual([A, B, A]);
    }
  });

  it('does not mistake a shared dependency (a diamond) for a cycle', () => {
    @Injectable()
    class Shared {}
    @Injectable()
    class Left {
      constructor(readonly shared: Shared) {}
    }
    @Injectable()
    class Right {
      constructor(readonly shared: Shared) {}
    }
    @Injectable()
    class Top {
      constructor(readonly left: Left, readonly right: Right) {}
    }
    const container = new Container();
    container.register(Top, Left, Right, Shared);

    const top = container.resolve(Top);

    expect(top.left.shared).toBe(top.right.shared);
  });
});
