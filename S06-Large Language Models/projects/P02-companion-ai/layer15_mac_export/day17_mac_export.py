"""
Layer 15 — Day 17: Mac Export
==============================
Converts the DPO Sama model to GGUF Q4_K_M format so it runs on a MacBook
with 18 GB RAM.  The output file is ~4 GB instead of 14 GB.

Run on the SERVER (not your Mac):
    python layer15_mac_export/day17_mac_export.py --setup
    python layer15_mac_export/day17_mac_export.py --convert
    python layer15_mac_export/day17_mac_export.py --quantize
    python layer15_mac_export/day17_mac_export.py --all       # all three steps
    python layer15_mac_export/day17_mac_export.py --status    # show what to download

Output:
    layer15_mac_export/results/sama_q4km.gguf   ~4 GB  ← download this to Mac
    layer15_mac_export/results/sama_f16.gguf    ~14 GB ← intermediate, delete after

What to download to Mac (see --status output for exact rsync commands):
    layer15_mac_export/results/sama_q4km.gguf
    layer15_mac_export/mac_chat.py
    layer15_mac_export/requirements_mac.txt
    checkpoints/crisis_classifier/   (476 MB)
    checkpoints/therapy_embedder/    (419 MB)
    data/splits/rag.json             (tiny)
    layer10_safety/training_data.json  (tiny, for crisis classifier path ref)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

DPO_MODEL_DIR  = BASE_DIR / "checkpoints" / "dpo_sama"
F16_GGUF       = RESULTS_DIR / "sama_f16.gguf"
Q4KM_GGUF      = RESULTS_DIR / "sama_q4km.gguf"

# llama.cpp is cloned here on the server (temporary build location)
LLAMA_CPP_DIR  = Path("/tmp/llama_cpp_build")

# llama-quantize binary produced by `make` (no cmake needed)
QUANTIZE_BIN   = LLAMA_CPP_DIR / "llama-quantize"


def run(cmd: str, cwd: Path | None = None) -> int:
    print(f"\n$ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode


def step_setup() -> bool:
    """Clone llama.cpp and build llama-quantize using make (no cmake needed)."""
    print("\n" + "=" * 60)
    print("STEP 1: Setup — clone llama.cpp + build llama-quantize")
    print("=" * 60)

    if not LLAMA_CPP_DIR.exists():
        rc = run("git clone --depth 1 https://github.com/ggerganov/llama.cpp /tmp/llama_cpp_build")
        if rc != 0:
            print("ERROR: git clone failed. Check internet connection.")
            return False
    else:
        print(f"  llama.cpp already cloned at {LLAMA_CPP_DIR}")

    # Install Python requirements for the convert script.
    # Use the specific requirements file — avoids numpy/cupy conflict from requirements.txt
    req_file = LLAMA_CPP_DIR / "requirements-convert_hf_to_gguf.txt"
    if not req_file.exists():
        req_file = LLAMA_CPP_DIR / "requirements.txt"
    rc = run(f"{sys.executable} -m pip install -q -r {req_file}")
    if rc != 0:
        print("WARNING: some requirements failed — will try converting anyway")

    # Build llama-quantize via cmake.
    # cmake may not be installed as a system package — install via pip if missing.
    cmake_bin = _find_or_install_cmake()
    if cmake_bin is None:
        print("ERROR: could not find or install cmake.")
        return False

    build_dir = LLAMA_CPP_DIR / "build_quantize"
    if QUANTIZE_BIN.exists():
        print(f"  llama-quantize already built at {QUANTIZE_BIN}")
    else:
        jobs = os.cpu_count() or 4
        print(f"  Building llama-quantize with cmake -j{jobs}...")
        rc = run(
            f"{cmake_bin} -B {build_dir} -DGGML_CUDA=OFF -DLLAMA_CURL=OFF .",
            cwd=LLAMA_CPP_DIR,
        )
        if rc != 0:
            print("ERROR: cmake configure failed.")
            return False
        rc = run(
            f"{cmake_bin} --build {build_dir} -j{jobs} --target llama-quantize",
            cwd=LLAMA_CPP_DIR,
        )
        if rc != 0:
            print("ERROR: cmake build failed.")
            return False
        # cmake puts the binary inside build_dir/bin/
        built_bin = build_dir / "bin" / "llama-quantize"
        if not built_bin.exists():
            print(f"ERROR: binary not found at {built_bin}")
            return False
        # Symlink to the expected location so the rest of the script finds it
        QUANTIZE_BIN.symlink_to(built_bin)

    print("\nSetup complete.")
    return True


def _find_or_install_cmake() -> str | None:
    """Return path to cmake binary, installing via pip if not on PATH."""
    # Check system PATH first
    result = subprocess.run("which cmake", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        cmake = result.stdout.strip()
        print(f"  cmake found at {cmake}")
        return cmake

    # Try venv bin (pip install cmake puts it there)
    venv_cmake = Path(sys.executable).parent / "cmake"
    if venv_cmake.exists():
        print(f"  cmake found at {venv_cmake}")
        return str(venv_cmake)

    # Not found — install cmake Python package which bundles the binary
    print("  cmake not found on system — installing via pip (cmake Python package)...")
    rc = subprocess.run(
        f"{sys.executable} -m pip install -q cmake",
        shell=True,
    ).returncode
    if rc != 0:
        return None

    if venv_cmake.exists():
        print(f"  cmake installed at {venv_cmake}")
        return str(venv_cmake)

    return None


def step_convert() -> bool:
    """Convert DPO safetensors to GGUF f16."""
    print("\n" + "=" * 60)
    print("STEP 2: Convert DPO model to GGUF f16")
    print("=" * 60)

    if F16_GGUF.exists():
        print(f"  {F16_GGUF.name} already exists, skipping convert.")
        return True

    convert_script = LLAMA_CPP_DIR / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        print(f"ERROR: Convert script not found at {convert_script}")
        print("  Run --setup first.")
        return False

    if not DPO_MODEL_DIR.exists():
        print(f"ERROR: DPO model not found at {DPO_MODEL_DIR}")
        return False

    print(f"  Input : {DPO_MODEL_DIR}")
    print(f"  Output: {F16_GGUF}")
    print("  This reads 14 GB and writes ~14 GB — takes a few minutes...")

    rc = run(
        f"{sys.executable} {convert_script} "
        f"{DPO_MODEL_DIR} "
        f"--outfile {F16_GGUF} "
        f"--outtype f16"
    )
    if rc != 0 or not F16_GGUF.exists():
        print("ERROR: Conversion failed.")
        return False

    size_gb = F16_GGUF.stat().st_size / 1e9
    print(f"\nConversion complete. {F16_GGUF.name} = {size_gb:.1f} GB")
    return True


def step_quantize() -> bool:
    """Quantize f16 GGUF to Q4_K_M (~4 GB)."""
    print("\n" + "=" * 60)
    print("STEP 3: Quantize f16 → Q4_K_M (~4 GB)")
    print("=" * 60)

    if Q4KM_GGUF.exists():
        size_gb = Q4KM_GGUF.stat().st_size / 1e9
        print(f"  {Q4KM_GGUF.name} already exists ({size_gb:.1f} GB), skipping quantize.")
        return True

    if not F16_GGUF.exists():
        print(f"ERROR: f16 GGUF not found at {F16_GGUF}")
        print("  Run --convert first.")
        return False

    if not QUANTIZE_BIN.exists():
        print(f"ERROR: llama-quantize not found at {QUANTIZE_BIN}")
        print("  Run --setup first.")
        return False

    print(f"  Input : {F16_GGUF} ({F16_GGUF.stat().st_size / 1e9:.1f} GB)")
    print(f"  Output: {Q4KM_GGUF}")
    print("  Quantizing to Q4_K_M — takes ~5 minutes...")

    rc = run(f"{QUANTIZE_BIN} {F16_GGUF} {Q4KM_GGUF} Q4_K_M")
    if rc != 0 or not Q4KM_GGUF.exists():
        print("ERROR: Quantization failed.")
        return False

    size_gb = Q4KM_GGUF.stat().st_size / 1e9
    print(f"\nQuantization complete. {Q4KM_GGUF.name} = {size_gb:.1f} GB")
    print(f"  You can now delete {F16_GGUF.name} to free 14 GB.")
    return True


def show_status() -> None:
    """Show what has been done and what to download to Mac."""
    print("\n" + "=" * 60)
    print("STATUS")
    print("=" * 60)

    checks = {
        "llama.cpp cloned":       LLAMA_CPP_DIR.exists(),
        "llama-quantize built":   QUANTIZE_BIN.exists(),
        "f16 GGUF created":       F16_GGUF.exists(),
        "Q4_K_M GGUF created":   Q4KM_GGUF.exists(),
    }
    for label, done in checks.items():
        mark = "✓" if done else "✗"
        print(f"  [{mark}] {label}")

    if Q4KM_GGUF.exists():
        size_gb = Q4KM_GGUF.stat().st_size / 1e9
        print(f"\n  Q4_K_M GGUF size: {size_gb:.1f} GB")
        print("\n" + "=" * 60)
        print("DOWNLOAD THESE FILES TO YOUR MAC")
        print("Run these rsync commands from your MacBook terminal:")
        print("=" * 60)

        server = "techvuser@192.168.29.49"
        remote = "/home/techvuser/lunar-workspace-dev/rough/code/handsonllm/project/P02-companion-ai"
        local  = "~/sama_mac"

        print(f"""
# 1. The model (~4 GB) — the big one
rsync -avh --progress \\
  {server}:{remote}/layer15_mac_export/results/sama_q4km.gguf \\
  {local}/checkpoints/

# 2. The chat script + requirements (tiny)
rsync -avh \\
  {server}:{remote}/layer15_mac_export/mac_chat.py \\
  {server}:{remote}/layer15_mac_export/requirements_mac.txt \\
  {local}/

# 3. Safety classifier (476 MB)
rsync -avh --progress \\
  {server}:{remote}/checkpoints/crisis_classifier/ \\
  {local}/checkpoints/crisis_classifier/

# 4. Therapy embedder for RAG + memory (419 MB)
rsync -avh --progress \\
  {server}:{remote}/checkpoints/therapy_embedder/ \\
  {local}/checkpoints/therapy_embedder/

# 5. RAG knowledge base (tiny)
rsync -avh \\
  {server}:{remote}/data/splits/rag.json \\
  {local}/data/splits/
""")
        print("Total download: ~5 GB")
        print("After downloading, run on Mac:")
        print(f"  cd {local}")
        print("  pip install -r requirements_mac.txt")
        print("  python mac_chat.py")
    else:
        print("\n  Q4_K_M GGUF not ready yet. Run: python day17_mac_export.py --all")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Sama DPO model for MacBook")
    parser.add_argument("--setup",    action="store_true", help="Clone llama.cpp and build quantize binary")
    parser.add_argument("--convert",  action="store_true", help="Convert DPO model to GGUF f16")
    parser.add_argument("--quantize", action="store_true", help="Quantize f16 GGUF to Q4_K_M")
    parser.add_argument("--all",      action="store_true", help="Run setup + convert + quantize")
    parser.add_argument("--status",   action="store_true", help="Show progress and download instructions")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if not any([args.setup, args.convert, args.quantize, args.all]):
        parser.print_help()
        return

    if args.all or args.setup:
        if not step_setup():
            sys.exit(1)

    if args.all or args.convert:
        if not step_convert():
            sys.exit(1)

    if args.all or args.quantize:
        if not step_quantize():
            sys.exit(1)

    show_status()


if __name__ == "__main__":
    main()
