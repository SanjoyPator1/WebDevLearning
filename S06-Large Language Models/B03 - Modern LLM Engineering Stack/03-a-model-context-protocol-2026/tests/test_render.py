# ============================================================
# TESTS: cafe_mcp.render — the documents, with no MCP in sight
# REF:   notes/04-resources.md
# ============================================================
#
# A resource hands back a DOCUMENT, and building a document is ordinary string
# work. Testing it here means the resource layer only has to be tested for its
# WIRING — the URI, the mime type, and the failure path.
#
# Run: pytest tests/test_render.py -v

import json

import pytest

from cafe_mcp import menu, render

# --- The menu document ---


def test_menu_markdown_lists_every_drink():
    document = render.menu_markdown()
    for drink in menu.DRINKS:
        assert drink.name in document, f"{drink.slug} missing from the menu document"


def test_menu_markdown_includes_the_slug_column():
    """The design choice from notes/04: a model that has read this document already
    holds the exact argument for `get_drink` or `cafe://drinks/<slug>`, so it never
    has to guess a slug or spend a turn on `list_drinks`. Remove the column and the
    document still looks fine while quietly costing a round trip."""
    document = render.menu_markdown()
    assert "| Slug |" in document
    for drink in menu.DRINKS:
        assert f"`{drink.slug}`" in document, f"slug {drink.slug} not in backticks"


def test_menu_markdown_marks_unavailable_sizes_explicitly():
    """A dash, not a blank. Blank cells read as *unknown*; a dash reads as *not
    sold*. When writing for a model, absence is the most easily misread thing you
    can put on a page."""
    document = render.menu_markdown()
    assert "A dash means that size is not sold" in document

    espresso_row = next(line for line in document.splitlines() if line.startswith("| Espresso |"))
    # S and M priced, L a dash.
    assert "$2.20" in espresso_row
    assert "$2.60" in espresso_row
    assert espresso_row.rstrip().endswith("| 63 | yes |")
    assert "—" in espresso_row


def test_menu_markdown_is_a_valid_looking_table():
    """Rows all have the same number of cells. A ragged markdown table renders as
    nonsense and a model will read it as nonsense too."""
    lines = [line for line in render.menu_markdown().splitlines() if line.startswith("|")]
    widths = {line.count("|") for line in lines}
    assert len(widths) == 1, f"ragged table: cell counts {widths}"


def test_menu_markdown_keeps_non_ascii_intact():
    """No mangling of Crème Brûlée on the way to the document. Topic 13 depends on
    this name surviving all the way to a header."""
    assert "Crème Brûlée Latte" in render.menu_markdown()


# --- The dairy-free document ---


def test_dairy_free_document_contains_only_dairy_free_drinks():
    # Match on the BACKTICKED SLUG, not the display name. "Latte" is a substring of
    # "Oat Latte", so a name-based assertion reports the dairy latte as present when
    # only the oat one is. `latte` is not a substring of `oat-latte` once the
    # backticks are included — which is a small argument for putting delimiters
    # around identifiers in generated documents.
    document = render.dairy_free_markdown()
    for drink in menu.DRINKS:
        marker = f"`{drink.slug}`"
        if drink.dairy_free:
            assert marker in document, f"{drink.slug} is dairy-free but missing"
        else:
            assert marker not in document, f"{drink.slug} contains dairy but is listed"


def test_dairy_free_document_is_much_shorter_than_the_full_menu():
    """The whole argument for addressing resources by URI: a host that knows the
    customer avoids dairy attaches this instead and spends a fraction of the
    tokens. If this ratio ever inverts, the narrow document has stopped being worth
    having."""
    assert len(render.dairy_free_markdown()) < len(render.menu_markdown())


# --- The single-drink document ---


def test_drink_json_is_parseable_and_complete():
    payload = json.loads(render.drink_json("flat-white"))
    assert payload["slug"] == "flat-white"
    assert payload["name"] == "Flat White"
    assert payload["available_sizes"] == ["S", "M", "L"]
    assert payload["caffeine_mg"] == 130


def test_drink_json_available_sizes_reflects_the_data():
    assert json.loads(render.drink_json("espresso"))["available_sizes"] == ["S", "M"]
    assert json.loads(render.drink_json("cold-brew"))["available_sizes"] == ["M", "L"]


def test_drink_json_raises_key_error_for_unknown_slug():
    """KeyError, deliberately — a plain Python failure. The RESOURCE layer converts
    it to ResourceNotFoundError, because the domain module should not know which
    envelope its caller lives in. Keep the conversion at the boundary."""
    with pytest.raises(KeyError):
        render.drink_json("no-such-drink")
