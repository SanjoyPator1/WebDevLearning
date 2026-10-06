# ============================================================
# LISTING: 04_output_types.py  (reference implementation -- FROM SCRATCH, no agents SDK)
# BUILDING: A hand-rolled strict-JSON-schema checker that reproduces, from
#           first principles, the SDK's real `UserError: Strict JSON
#           schema is enabled, but the output type is not valid` -- for
#           the exact same reason: a dict keyed by arbitrary integers has
#           no fixed, closed set of `properties` a strict schema can
#           declare.
# REF: Chapter 2 notes, section 8 (Typed Outputs and the Strict-JSON Wall)
# COMPARE: the SDK version of this file at ../../openai_sdk/template/04_output_types.py
#          (this chapter's solved/ reference was never filled in, so the
#          notes themselves are ground truth here, not a solved/ file)
# ============================================================
#
# In the SDK version, `output_type=ResearchPlanModel` with `tasks:
# dict[int, str]` raises before any network call because the SDK's OWN
# internal schema-builder converts your Pydantic model to a strict JSON
# Schema and rejects it on the way. We have no such built-in schema
# builder protecting us here -- so this file builds a small, honest one
# by hand and uses it to reproduce the identical lesson: this failure is
# 100% client-side and pre-network. It reproduces identically whether
# `client` above is pointed at Gemini, Ollama, real OpenAI, or Bedrock --
# swapping providers will never fix it, because no provider is involved
# yet. Notice this file never even gets as far as constructing a
# `client` variable for that reason -- the check has to run before any
# network call could conceivably happen.

# --- Your turn ---
# Implement assert_strict_json_schema(schema: dict) -> None below,
# exactly per its docstring spec. Then, further down, construct the
# broken schema this file is named for and call the function on it to
# demonstrate the raise.


def assert_strict_json_schema(schema: dict) -> None:
    """Check a JSON Schema dict against the two rules OpenAI's real
    strict-mode schema builder enforces, recursively, at every
    object-typed node in the schema (a node is "object-typed" if its
    `type` is `"object"`, or if it has a `properties` key at all):

    1. `additionalProperties` must be present on that node AND must be
       exactly the Python value `False` -- not absent (missing the key
       entirely), and not a nested sub-schema dict (e.g.
       `{"type": "string"}`), which is what an "open-ended dict of
       arbitrary keys" has to use instead, since there's no way to list
       arbitrary keys as fixed `properties`.

    2. Every key that appears under that node's `properties` must also
       appear in that node's `required` list. (A key present in
       `properties` but missing from `required` is what the SDK calls an
       optional field -- strict mode has a different way to express
       optionality, via `anyOf: [..., {"type": "null"}]`, but a bare
       missing-from-required key is not allowed on its own.)

    This function must recurse into every part of the schema tree where
    another object-typed node could appear -- values under `properties`,
    the `items` of an array-typed node, and so on -- not just check the
    top level. A violation anywhere in the tree must raise, not just a
    violation at the root.

    On the first rule violation found (checked in the order: rule 1
    before rule 2, at each node, in the order nodes are visited), raise
    `ValueError` with a message that explains WHY, in the same spirit as
    the SDK's real error -- name the offending node's location, and say
    plainly that this is because an open-ended/arbitrary-keys shape can't
    be expressed as a JSON Schema's fixed, closed `properties` object.

    Returns None (no exception) if the schema is valid.

    This function must do NO network I/O and must not construct or
    require an API client -- the whole point is that this check runs
    before any client is even built, matching the SDK's real behavior of
    raising `UserError` before any request is sent.
    """
    raise NotImplementedError("implement the recursive strict-schema check per the docstring above")


# --- Your turn (continued) ---
# Build the ACTUAL broken schema this file is named for: the honest,
# correct JSON Schema representation of "a dict keyed by arbitrary
# integers, valued by strings" is
#   {"type": "object", "additionalProperties": {"type": "string"},
#    "properties": {}, "required": []}
# -- no fixed key set is possible for arbitrary integer keys, so
# additionalProperties has to be an open sub-schema, not False.
#
# Wrap that as the `tasks` field of an outer, otherwise-strict object:
#   {"type": "object",
#    "properties": {"tasks": <the dict-of-arbitrary-keys schema above>},
#    "required": ["tasks"],
#    "additionalProperties": False}
#
# Call assert_strict_json_schema(...) on the wrapped schema inside a
# try/except ValueError block, and print the caught error message
# clearly -- mirroring the SDK's real behavior of raising before any
# network call.
