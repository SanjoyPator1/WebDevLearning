# ============================================================
# TESTS: cafe_mcp.menu — the domain, with no MCP in sight
# REF:   notes/02-tools-list.md
# ============================================================
#
# There is no server here, no transport, no async, no event loop. That is the
# payoff of `menu.py` importing nothing from MCP: the café's rules can be tested
# at the speed of a function call.
#
# Run: pytest tests/test_menu.py -v

from cafe_mcp import menu


def test_menu_has_twelve_drinks():
    """A fixed count, so accidentally deleting a drink is a test failure."""
    assert len(menu.DRINKS) == 12


def test_menu_order_is_stable():
    """The spec asks for deterministic ordering, and topic 02 explains why it is
    about prompt-cache hit rates rather than tidiness. A tuple guarantees it; this
    test guards against someone turning it into a set or a dict later."""
    first_pass = [d.slug for d in menu.all_drinks()]
    second_pass = [d.slug for d in menu.all_drinks()]
    assert first_pass == second_pass
    assert first_pass[0] == "espresso", "menu order changed — was that deliberate?"


def test_slugs_are_unique_and_well_formed():
    """Slugs are the identifier the model passes back to us, so they must be
    unique and predictable. Lowercase-with-hyphens is what `get_drink`'s argument
    description promises the model, so it had better be true."""
    slugs = [d.slug for d in menu.DRINKS]
    assert len(slugs) == len(set(slugs)), "duplicate slug"
    for slug in slugs:
        assert slug == slug.lower(), f"{slug!r} is not lowercase"
        assert " " not in slug, f"{slug!r} contains a space"
        assert "_" not in slug, f"{slug!r} uses an underscore, not a hyphen"


def test_every_drink_is_sold_in_at_least_one_size():
    """A drink with no prices could never be ordered, so it should not exist."""
    for drink in menu.DRINKS:
        assert drink.prices, f"{drink.slug} has no prices"


def test_prices_only_use_known_sizes():
    """Guards against a typo like "XL" or "m" creeping into the data, which would
    make `sizes_for` silently drop it."""
    for drink in menu.DRINKS:
        for size in drink.prices:
            assert size in menu.SIZES, f"{drink.slug} has unknown size {size!r}"


def test_find_returns_the_drink():
    drink = menu.find("flat-white")
    assert drink is not None
    assert drink.name == "Flat White"


def test_find_returns_none_for_unknown_slug():
    """None, not an exception. The MENU does not decide how a missing drink is
    reported to a model — the tool layer does, with ToolError. Topic 03."""
    assert menu.find("no-such-drink") is None


def test_sizes_for_returns_s_m_l_order():
    """Not insertion order of the prices dict — S/M/L order, always, so the model
    sees a consistent shape."""
    assert menu.sizes_for("flat-white") == ("S", "M", "L")


def test_sizes_for_omits_missing_sizes():
    """These irregularities exist in the data specifically so topic 03 has a real
    validation path to exercise."""
    assert menu.sizes_for("espresso") == ("S", "M"), "espresso has no large"
    assert menu.sizes_for("cold-brew") == ("M", "L"), "cold brew has no small"
    assert menu.sizes_for("creme-brulee-latte") == ("M", "L")


def test_sizes_for_unknown_slug_is_empty():
    assert menu.sizes_for("no-such-drink") == ()


def test_price_of_known_combination():
    assert menu.price_of("latte", "L") == 4.30


def test_price_of_unsold_combination_is_none():
    """This is the exact condition `quote` turns into a ToolError in topic 03.
    Testing it here means the tool layer only has to be tested for its MESSAGE."""
    assert menu.price_of("espresso", "L") is None


def test_price_of_unknown_slug_is_none():
    assert menu.price_of("no-such-drink", "M") is None


def test_dairy_free_drinks_exist():
    """Topic 05's prompt filters on this, so there had better be some."""
    dairy_free = [d.slug for d in menu.DRINKS if d.dairy_free]
    assert "oat-latte" in dairy_free
    assert "americano" in dairy_free


def test_one_drink_has_a_non_ascii_name():
    """Topic 13 needs this: `Mcp-Name` and `Mcp-Param-*` headers cannot carry raw
    non-ASCII, so a name like this forces the base64 sentinel encoding. If someone
    "cleans up" the menu, that lesson quietly loses its subject."""
    names = [d.name for d in menu.DRINKS]
    assert any(not name.isascii() for name in names), "no non-ASCII drink name left"
    assert menu.find("creme-brulee-latte").name == "Crème Brûlée Latte"
