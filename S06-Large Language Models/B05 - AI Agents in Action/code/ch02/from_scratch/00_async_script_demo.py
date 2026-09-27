# ============================================================
# TOPIC: asyncio.run() in a real script (the part Jupyter can't show)
# MATH:  T_sync = t1 + t2 + ... + tn   vs   T_async ≈ max(t1, ..., tn)
# REF:   B05 ch02 from_scratch, companion to 00_async_python_basics.ipynb (sections 4 and 15)
# ============================================================
#
# Run from a terminal:
#     python 00_async_script_demo.py
#
# In Jupyter an event loop is already running, so you never see one being
# created or closed. Here nothing async exists until asyncio.run(main())
# starts a loop, and it is gone again once main() returns.

# --- Imports ---
import asyncio
import time

# --- Shared clock so every log line shows WHEN it happened ---
CLOCK_START = time.perf_counter()


def reset_clock():
    """
    Restart the shared clock at zero.

    Returns:
        None
    """
    global CLOCK_START
    CLOCK_START = time.perf_counter()


def log(message):
    """
    Print a message with the seconds passed since the last reset_clock().

    Args:
        message (str): what just happened
    Returns:
        None
    """
    elapsed_seconds = time.perf_counter() - CLOCK_START
    print(f"  [t={elapsed_seconds:5.2f}s] {message}")


def has_running_loop():
    """
    Check whether an event loop is running right now, in this thread.

    Returns:
        bool: True inside async code started by asyncio.run(), False in plain code
    """
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


# --- Core Implementation ---
async def make_order(item_name, cook_seconds):
    """
    Pretend to cook one item: wait without blocking, then return a message.

    Args:
        item_name (str): what we're cooking
        cook_seconds (float): how long the fake cooking takes
    Returns:
        str: e.g. "chai is ready"
    Note: asyncio.sleep stands in for a real wait, like an API call.
    """
    log(f"start {item_name} ({cook_seconds}s)")
    await asyncio.sleep(cook_seconds)
    log(f"done  {item_name}")
    return f"{item_name} is ready"


async def cook_one_by_one():
    """
    Await three orders one after another.

    Returns:
        float: seconds taken (expected ≈ 0.5 + 1.0 + 1.5 = 3.0s)
    """
    reset_clock()
    start_time = time.perf_counter()
    await make_order("chai", 0.5)
    await make_order("toast", 1.0)
    await make_order("omelette", 1.5)
    return time.perf_counter() - start_time


async def cook_together():
    """
    Start all three orders at once with gather, then wait for all of them.

    Returns:
        float: seconds taken (expected ≈ max(0.5, 1.0, 1.5) = 1.5s)
    """
    reset_clock()
    start_time = time.perf_counter()
    await asyncio.gather(
        make_order("chai", 0.5),
        make_order("toast", 1.0),
        make_order("omelette", 1.5),
    )
    return time.perf_counter() - start_time


async def try_nested_asyncio_run():
    """
    Call asyncio.run() from inside async code, to show why that is not allowed.

    Returns:
        str: the error message Python raises
    """
    inner_coroutine = make_order("inner chai", 0.1)
    try:
        asyncio.run(inner_coroutine)
        return "no error (unexpected)"
    except RuntimeError as error:
        inner_coroutine.close()   # it never ran; close it so Python doesn't warn
        return str(error)


async def main():
    """
    The single entry point. Every await in the program lives under here.

    Returns:
        dict: timings from the demos, handed back to whoever called asyncio.run(main())
    """
    print(f"\n  inside main(): is a loop running? {has_running_loop()}")

    print("\n" + "-" * 60)
    print("STEP 2: await one by one (still sequential)")
    print("-" * 60)
    sequential_seconds = await cook_one_by_one()
    print(f"  total: {sequential_seconds:.2f}s   (expected ≈ 0.5 + 1.0 + 1.5 = 3.0s)")

    print("\n" + "-" * 60)
    print("STEP 3: asyncio.gather (all together)")
    print("-" * 60)
    together_seconds = await cook_together()
    print(f"  total: {together_seconds:.2f}s   (expected ≈ max(0.5, 1.0, 1.5) = 1.5s)")

    print("\n" + "-" * 60)
    print("STEP 4: calling asyncio.run() again INSIDE async code")
    print("-" * 60)
    nested_error = await try_nested_asyncio_run()
    print(f"  RuntimeError: {nested_error}")
    print("  -> same error Jupyter gives: one loop per program, started once, from plain code")

    return {"sequential_seconds": round(sequential_seconds, 2), "together_seconds": round(together_seconds, 2)}


# --- Run ---
if __name__ == "__main__":
    print("-" * 60)
    print("STEP 0: plain code, before asyncio.run()")
    print("-" * 60)
    print(f"  is a loop running? {has_running_loop()}")

    forgotten_main = main()   # calling an async function WITHOUT running it
    print(f"  main() on its own gives back: {type(forgotten_main).__name__} object (nothing ran)")
    forgotten_main.close()    # tidy up so Python doesn't warn "coroutine was never awaited"

    print("\n" + "-" * 60)
    print("STEP 1: asyncio.run(main()) creates the loop, runs main to the end, closes the loop")
    print("-" * 60)
    demo_summary = asyncio.run(main())   # blocks here until main() returns

    print("\n" + "-" * 60)
    print("STEP 5: back in plain code, after asyncio.run()")
    print("-" * 60)
    print(f"  is a loop running? {has_running_loop()}   (the loop was closed)")
    print(f"  asyncio.run() returned main()'s return value: {demo_summary}")

# ===== OUTPUT =====

# ------------------------------------------------------------
# STEP 0: plain code, before asyncio.run()
# ------------------------------------------------------------
#   is a loop running? False
#   main() on its own gives back: coroutine object (nothing ran)

# ------------------------------------------------------------
# STEP 1: asyncio.run(main()) creates the loop, runs main to the end, closes the loop
# ------------------------------------------------------------

#   inside main(): is a loop running? True

# ------------------------------------------------------------
# STEP 2: await one by one (still sequential)
# ------------------------------------------------------------
#   [t= 0.00s] start chai (0.5s)
#   [t= 0.50s] done  chai
#   [t= 0.50s] start toast (1.0s)
#   [t= 1.50s] done  toast
#   [t= 1.50s] start omelette (1.5s)
#   [t= 3.00s] done  omelette
#   total: 3.00s   (expected ≈ 0.5 + 1.0 + 1.5 = 3.0s)

# ------------------------------------------------------------
# STEP 3: asyncio.gather (all together)
# ------------------------------------------------------------
#   [t= 0.00s] start chai (0.5s)
#   [t= 0.00s] start toast (1.0s)
#   [t= 0.00s] start omelette (1.5s)
#   [t= 0.50s] done  chai
#   [t= 1.00s] done  toast
#   [t= 1.50s] done  omelette
#   total: 1.50s   (expected ≈ max(0.5, 1.0, 1.5) = 1.5s)

# ------------------------------------------------------------
# STEP 4: calling asyncio.run() again INSIDE async code
# ------------------------------------------------------------
#   RuntimeError: asyncio.run() cannot be called from a running event loop
#   -> same error Jupyter gives: one loop per program, started once, from plain code

# ------------------------------------------------------------
# STEP 5: back in plain code, after asyncio.run()
# ------------------------------------------------------------
#   is a loop running? False   (the loop was closed)
#   asyncio.run() returned main()'s return value: {'sequential_seconds': 3.0, 'together_seconds': 1.5}
