"""
Phase 8 — Mac Export
=====================
Converts the DPO VILLAINBOT model to GGUF format for MacBook.
14 GB safetensors → quantized GGUF via llama-cpp-python with Metal GPU.

Quant options (--quant):
    Q8_0    ~8 GB   best quality  — recommended for 18 GB M3/M4
    Q5_K_M  ~5 GB   great quality — recommended for 16 GB
    Q4_K_M  ~4 GB   good quality  — recommended for 8 GB

Run on the SERVER (not your Mac):
    python phase8/phase8_mac_export.py --all               # Q8_0 (default)
    python phase8/phase8_mac_export.py --all --quant Q5_K_M
    python phase8/phase8_mac_export.py --all --quant Q4_K_M
    python phase8/phase8_mac_export.py --status            # show rsync commands

Output:
    phase8/results/villainbot_q8.gguf    ~8 GB  (Q8_0)
    phase8/results/villainbot_q5km.gguf  ~5 GB  (Q5_K_M)
    phase8/results/villainbot_q4km.gguf  ~4 GB  (Q4_K_M)
    phase8/results/villainbot_f16.gguf  ~14 GB  ← intermediate, delete after
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

DPO_MODEL_DIR = BASE_DIR / "checkpoints" / "dpo_villainbot"
F16_GGUF      = RESULTS_DIR / "villainbot_f16.gguf"

QUANT_OUTPUTS = {
    "Q8_0":   RESULTS_DIR / "villainbot_q8.gguf",
    "Q5_K_M": RESULTS_DIR / "villainbot_q5km.gguf",
    "Q4_K_M": RESULTS_DIR / "villainbot_q4km.gguf",
}
QUANT_SIZES = {"Q8_0": "~8 GB", "Q5_K_M": "~5 GB", "Q4_K_M": "~4 GB"}

LLAMA_CPP_DIR = Path("/tmp/llama_cpp_build")
QUANTIZE_BIN  = LLAMA_CPP_DIR / "llama-quantize"


def run(cmd: str, cwd: Path | None = None) -> int:
    print(f"\n$ {cmd}")
    return subprocess.run(cmd, shell=True, cwd=cwd).returncode


def _find_or_install_cmake() -> str | None:
    result = subprocess.run("which cmake", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        cmake = result.stdout.strip()
        print(f"  cmake found at {cmake}")
        return cmake

    venv_cmake = Path(sys.executable).parent / "cmake"
    if venv_cmake.exists():
        print(f"  cmake found at {venv_cmake}")
        return str(venv_cmake)

    print("  cmake not found — installing via pip...")
    rc = subprocess.run(f"{sys.executable} -m pip install -q cmake", shell=True).returncode
    if rc != 0:
        return None
    return str(venv_cmake) if venv_cmake.exists() else None


def step_setup() -> bool:
    print("\n" + "=" * 60)
    print("STEP 1: Setup — clone llama.cpp + build llama-quantize")
    print("=" * 60)

    if not LLAMA_CPP_DIR.exists():
        rc = run("git clone --depth 1 https://github.com/ggerganov/llama.cpp /tmp/llama_cpp_build")
        if rc != 0:
            print("ERROR: git clone failed.")
            return False
    else:
        print(f"  llama.cpp already cloned at {LLAMA_CPP_DIR}")

    req_file = LLAMA_CPP_DIR / "requirements-convert_hf_to_gguf.txt"
    if not req_file.exists():
        req_file = LLAMA_CPP_DIR / "requirements.txt"
    run(f"{sys.executable} -m pip install -q -r {req_file}")

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
        rc = run(f"{cmake_bin} -B {build_dir} -DGGML_CUDA=OFF -DLLAMA_CURL=OFF .", cwd=LLAMA_CPP_DIR)
        if rc != 0:
            print("ERROR: cmake configure failed.")
            return False
        rc = run(f"{cmake_bin} --build {build_dir} -j{jobs} --target llama-quantize", cwd=LLAMA_CPP_DIR)
        if rc != 0:
            print("ERROR: cmake build failed.")
            return False
        built_bin = build_dir / "bin" / "llama-quantize"
        if not built_bin.exists():
            print(f"ERROR: binary not found at {built_bin}")
            return False
        QUANTIZE_BIN.symlink_to(built_bin)

    print("\nSetup complete.")
    return True


def step_convert() -> bool:
    print("\n" + "=" * 60)
    print("STEP 2: Convert DPO model to GGUF f16")
    print("=" * 60)

    if F16_GGUF.exists():
        print(f"  {F16_GGUF.name} already exists, skipping.")
        return True

    convert_script = LLAMA_CPP_DIR / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        print("ERROR: convert_hf_to_gguf.py not found. Run --setup first.")
        return False

    if not DPO_MODEL_DIR.exists():
        print(f"ERROR: DPO model not found at {DPO_MODEL_DIR}")
        return False

    print(f"  Input : {DPO_MODEL_DIR}")
    print(f"  Output: {F16_GGUF}")
    print("  Reading 14 GB safetensors → writing ~14 GB f16 GGUF, takes a few minutes...")

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


def step_quantize(quant: str) -> bool:
    out_gguf = QUANT_OUTPUTS[quant]
    size_str = QUANT_SIZES[quant]

    print("\n" + "=" * 60)
    print(f"STEP 3: Quantize f16 → {quant} ({size_str})")
    print("=" * 60)

    if out_gguf.exists():
        size_gb = out_gguf.stat().st_size / 1e9
        print(f"  {out_gguf.name} already exists ({size_gb:.1f} GB), skipping.")
        return True

    if not F16_GGUF.exists():
        print("ERROR: f16 GGUF not found. Run --convert first.")
        return False

    if not QUANTIZE_BIN.exists():
        print("ERROR: llama-quantize not found. Run --setup first.")
        return False

    print(f"  Input : {F16_GGUF} ({F16_GGUF.stat().st_size / 1e9:.1f} GB)")
    print(f"  Output: {out_gguf}")
    print(f"  Quantizing to {quant} — takes ~5 minutes...")

    rc = run(f"{QUANTIZE_BIN} {F16_GGUF} {out_gguf} {quant}")
    if rc != 0 or not out_gguf.exists():
        print("ERROR: Quantization failed.")
        return False

    size_gb = out_gguf.stat().st_size / 1e9
    print(f"\nQuantization complete. {out_gguf.name} = {size_gb:.1f} GB")
    print(f"  You can now delete {F16_GGUF.name} to free ~14 GB:")
    print(f"  rm {F16_GGUF}")
    return True


def show_status(quant: str) -> None:
    out_gguf = QUANT_OUTPUTS[quant]
    size_str = QUANT_SIZES[quant]

    print("\n" + "=" * 60)
    print("STATUS")
    print("=" * 60)

    checks = {
        "llama.cpp cloned":          LLAMA_CPP_DIR.exists(),
        "llama-quantize built":      QUANTIZE_BIN.exists(),
        "f16 GGUF created":          F16_GGUF.exists(),
        f"{quant} GGUF created":     out_gguf.exists(),
    }
    for label, done in checks.items():
        mark = "v" if done else "x"
        print(f"  [{mark}] {label}")

    remote_base = "/home/techvuser/lunar-workspace-dev/rough/code/handsonllm/project/P03-villain-bot"

    if out_gguf.exists():
        size_gb = out_gguf.stat().st_size / 1e9
        print(f"\n  {quant} GGUF size: {size_gb:.1f} GB")
        print("\n" + "=" * 60)
        print("RSYNC THESE TO YOUR MAC (run from your MacBook terminal):")
        print("=" * 60)
        print(f"""
# 1. The model ({size_str})
rsync -avh --progress \\
  techv-lunar:{remote_base}/phase8/results/{out_gguf.name} \\
  ~/villainbot_mac/

# 2. The Mac chat script + requirements (tiny)
rsync -avh \\
  techv-lunar:{remote_base}/phase8/mac_chat.py \\
  techv-lunar:{remote_base}/phase8/requirements_mac.txt \\
  ~/villainbot_mac/

# Then on Mac:
cd ~/villainbot_mac
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python
pip install -r requirements_mac.txt
python mac_chat.py --gguf {out_gguf.name}
""")
    else:
        print(f"\n  {quant} GGUF not ready. Run: python phase8/phase8_mac_export.py --all --quant {quant}")


def main() -> None:
    parser = argparse.ArgumentParser(description="VILLAINBOT Phase 8 — Mac Export")
    parser.add_argument("--setup",    action="store_true", help="Clone llama.cpp and build quantize binary")
    parser.add_argument("--convert",  action="store_true", help="Convert DPO model to GGUF f16")
    parser.add_argument("--quantize", action="store_true", help="Quantize f16 GGUF")
    parser.add_argument("--all",      action="store_true", help="Run all three steps")
    parser.add_argument("--status",   action="store_true", help="Show progress and rsync instructions")
    parser.add_argument(
        "--quant",
        default="Q8_0",
        choices=list(QUANT_OUTPUTS.keys()),
        help="Quantization level (default: Q8_0 — best for 18 GB M3/M4)",
    )
    args = parser.parse_args()

    if args.status:
        show_status(args.quant)
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
        if not step_quantize(args.quant):
            sys.exit(1)

    show_status(args.quant)


if __name__ == "__main__":
    main()
