"""
tools/lists.py

add_to_list  — add items to a named list (groceries, todos, etc.)
read_list    — display all items in a named list
remove_from_list — remove a specific item
clear_list   — wipe a list entirely
"""
import json
import config
from scout.memory.manager import _load_semantic, _save_semantic


def add_to_list(list_name: str, items: list[str]) -> str:
    """
    Add one or more items to a named list stored in user_memory.json.
    list_name examples: 'groceries', 'todos', 'shopping'
    """
    list_name = list_name.lower().strip()
    data = _load_semantic()
    lst = data.setdefault("lists", {}).setdefault(list_name, [])

    added = []
    already = []
    for item in items:
        item = item.strip()
        if item and item not in lst:
            lst.append(item)
            added.append(item)
        elif item in lst:
            already.append(item)

    _save_semantic(data)

    parts = []
    if added:
        parts.append(f"✅ Added to *{list_name}*: {', '.join(added)}")
    if already:
        parts.append(f"(Already on list: {', '.join(already)})")
    parts.append(f"\n📋 *{list_name.capitalize()}* now has: {', '.join(lst)}")
    return "\n".join(parts)


def read_list(list_name: str) -> str:
    """Read all items in a named list."""
    list_name = list_name.lower().strip()
    data = _load_semantic()
    lst = data.get("lists", {}).get(list_name, [])

    if not lst:
        return f"📭 Your *{list_name}* list is empty."

    lines = [f"📋 *{list_name.capitalize()}* ({len(lst)} items):"]
    for i, item in enumerate(lst, 1):
        lines.append(f"  {i}. {item}")
    return "\n".join(lines)


def remove_from_list(list_name: str, item: str) -> str:
    """Remove a specific item from a named list."""
    list_name = list_name.lower().strip()
    item = item.strip()
    data = _load_semantic()
    lst = data.get("lists", {}).get(list_name, [])

    if item not in lst:
        return f"❌ '{item}' not found in *{list_name}*."

    lst.remove(item)
    _save_semantic(data)
    return f"🗑️ Removed '{item}' from *{list_name}*. Remaining: {', '.join(lst) or '(empty)'}"


def clear_list(list_name: str) -> str:
    """Clear all items from a named list."""
    list_name = list_name.lower().strip()
    data = _load_semantic()
    if list_name in data.get("lists", {}):
        data["lists"][list_name] = []
        _save_semantic(data)
        return f"🗑️ Cleared *{list_name}* list."
    return f"❌ No list named '{list_name}' found."


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(add_to_list("groceries", ["milk", "eggs", "bread"]))
    print(read_list("groceries"))
    print(remove_from_list("groceries", "eggs"))
    print(read_list("groceries"))
