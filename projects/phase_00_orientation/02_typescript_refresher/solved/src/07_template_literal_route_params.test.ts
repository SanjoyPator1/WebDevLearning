import { describe, expect, expectTypeOf, it } from 'vitest';
import {
  extractParams,
  type RouteKey,
  type RouteParams,
} from './07_template_literal_route_params.js';

describe('07 template literal route params', () => {
  it('RouteParams extracts one parameter', () => {
    expectTypeOf<RouteParams<'/users/:id'>>().toEqualTypeOf<{ id: string }>();
  });

  it('RouteParams extracts several parameters', () => {
    expectTypeOf<RouteParams<'/users/:id/posts/:postId'>>().toEqualTypeOf<{
      id: string;
      postId: string;
    }>();
    expectTypeOf<RouteParams<'/:a/:b/:c'>>().toEqualTypeOf<{
      a: string;
      b: string;
      c: string;
    }>();
  });

  it('RouteParams is empty when there are no parameters', () => {
    expectTypeOf<keyof RouteParams<'/health'>>().toBeNever();
  });

  it('RouteKey only allows known methods followed by a path', () => {
    expectTypeOf<'GET /users'>().toExtend<RouteKey>();
    expectTypeOf<'POST /users/1'>().toExtend<RouteKey>();
    expectTypeOf<'PUT /users'>().not.toExtend<RouteKey>();
    expectTypeOf<'GET users'>().not.toExtend<RouteKey>();
  });

  it('extractParams returns the values with a typed result', () => {
    const params = extractParams('/users/:id/posts/:postId', '/users/7/posts/42');
    expect(params).toEqual({ id: '7', postId: '42' });
    expectTypeOf(params).toEqualTypeOf<{ id: string; postId: string }>();
  });

  it('extractParams rejects paths that do not match', () => {
    expect(() => extractParams('/users/:id', '/posts/7')).toThrow('does not match');
    expect(() => extractParams('/users/:id', '/users/7/extra')).toThrow(
      'does not match',
    );
  });

  it('extractParams does not allow reading a parameter that is not in the pattern', () => {
    const params = extractParams('/users/:id', '/users/7');
    // @ts-expect-error 'postId' is not a parameter of this pattern
    void params.postId;
  });
});
