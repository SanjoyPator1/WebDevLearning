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
    _walk_schema_node(schema, path="$")


def _walk_schema_node(node: object, path: str) -> None:
    """Recurse through a JSON Schema value (which may be a dict, a list,
    or a plain leaf value like a string/int/bool) and run the two
    strict-mode checks on every object-typed dict node found along the
    way. `path` is a breadcrumb trail used purely to make the eventual
    error message point at *where* in the schema things went wrong."""
    if isinstance(node, dict):
        node_is_object_typed = node.get("type") == "object" or "properties" in node
        if node_is_object_typed:
            _check_object_node_is_strict(node, path)

        # Recurse into every value in this dict -- this is what makes the
        # walk generic enough to find object nodes nested under
        # `properties`, `items`, `anyOf`, `$defs`, or anywhere else a
        # sub-schema might live, without hard-coding those key names.
        for key, value in node.items():
            _walk_schema_node(value, path=f"{path}.{key}")

    elif isinstance(node, list):
        for index, item in enumerate(node):
            _walk_schema_node(item, path=f"{path}[{index}]")

    # Any other leaf type (str, int, bool, None) has nothing to recurse
    # into and is never itself an object-typed node.


def _check_object_node_is_strict(node: dict, path: str) -> None:
    """Apply the two strict-mode rules to a single object-typed node.
    Rule 1 is checked before rule 2, matching the docstring's spec."""
    additional_properties = node.get("additionalProperties", "<MISSING>")
    if additional_properties is not False:
        raise ValueError(
            f"Strict JSON schema requires additionalProperties: false and "
            f"every property to be required (violation at {path!r}). "
            f"This node's additionalProperties is {additional_properties!r}, "
            f"which allows open-ended keys -- that can't be expressed as a "
            f"fixed set of properties, which is exactly why a dict keyed by "
            f"arbitrary integers (or any arbitrary key) fails strict mode."
        )

    properties = node.get("properties", {})
    required = node.get("required", [])
    keys_missing_from_required = [key for key in properties if key not in required]
    if keys_missing_from_required:
        raise ValueError(
            f"Strict JSON schema requires additionalProperties: false and "
            f"every property to be required (violation at {path!r}). "
            f"These properties are declared but not listed in `required`: "
            f"{keys_missing_from_required}."
        )


def build_broken_arbitrary_keys_schema() -> dict:
    """Build the JSON Schema this file is named for: the honest, correct
    representation of `tasks: dict[int, str]` -- a dict keyed by
    arbitrary integers, valued by strings. Because no fixed key set can
    be listed for arbitrary keys, `additionalProperties` has to be an
    open sub-schema (`{"type": "string"}`) rather than `False` -- and
    that is precisely the shape strict mode forbids."""
    arbitrary_keys_dict_schema = {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "properties": {},
        "required": [],
    }
    return {
        "type": "object",
        "properties": {"tasks": arbitrary_keys_dict_schema},
        "required": ["tasks"],
        "additionalProperties": False,
    }


def build_valid_strict_schema() -> dict:
    """A schema that SHOULD pass -- `tasks: list[Task]` where `Task` is
    a closed, fully-required object. Included purely so the checker's
    behavior on a valid schema is visible right next to its behavior on
    the broken one, not just asserted in a comment."""
    task_item_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "description": {"type": "string"},
        },
        "required": ["id", "description"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"tasks": {"type": "array", "items": task_item_schema}},
        "required": ["tasks"],
        "additionalProperties": False,
    }


def main():
    print("=" * 60)
    print("STEP 1: Checking a VALID strict schema (list[Task], closed and")
    print("        fully required) -- expect no error")
    print("=" * 60)
    valid_schema = build_valid_strict_schema()
    print(f"  schema: {valid_schema}")
    try:
        assert_strict_json_schema(valid_schema)
        print("  PASSED: assert_strict_json_schema raised nothing.")
    except ValueError as error:
        print(f"  UNEXPECTED FAILURE: {error}")

    print("\n" + "=" * 60)
    print("STEP 2: Checking the BROKEN schema for tasks: dict[int, str]")
    print("        -- this is the schema that models what dict[int, str]")
    print("        actually needs (an open additionalProperties sub-schema)")
    print("=" * 60)
    broken_schema = build_broken_arbitrary_keys_schema()
    print(f"  schema: {broken_schema}")

    print("\n" + "=" * 60)
    print("STEP 3: Running the check -- expect a ValueError, and note this")
    print("        happens with NO client constructed and NO network call")
    print("        made, exactly like the SDK's real pre-network UserError")
    print("=" * 60)
    try:
        assert_strict_json_schema(broken_schema)
        print("  UNEXPECTED: no error was raised for the broken schema.")
    except ValueError as error:
        print(f"  Caught ValueError, as expected:\n    {error}")


if __name__ == "__main__":
    main()
