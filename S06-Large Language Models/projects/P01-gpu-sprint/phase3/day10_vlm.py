"""
Day 10 — Multimodal: Fine-tune a Vision-Language Model

Part A: Run Qwen2.5-VL-7B on test images — probe where base model fails
Part B: Prepare a fine-tuning dataset (screenshots or your own images)
Part C: Fine-tune with LLaMA-Factory (CLI wrapper + dataset prep)
Part D: Evaluate base vs fine-tuned side by side

Run:
    python day10_vlm.py --part probe              # test base model on sample images
    python day10_vlm.py --part prep_data          # prepare dataset for LLaMA-Factory
    python day10_vlm.py --part eval --base_only   # evaluate base model
    python day10_vlm.py --part eval --compare     # evaluate base vs fine-tuned

For fine-tuning itself, use LLaMA-Factory CLI after running prep_data:
    llamafactory-cli train vlm_lora_config.yaml
"""

import argparse
import json
from pathlib import Path

import requests
import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

RESULTS_DIR = Path(__file__).parent / "results"
DATA_DIR = Path(__file__).parent / "vlm_data"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "day10"
RESULTS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

VLM_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"

# Public domain test images (replace with your own domain images)
TEST_IMAGES = [
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png",
        "question": "What do you see in this image? Describe the objects and their arrangement.",
        "type": "object",
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Stonehenge.jpg/640px-Stonehenge.jpg",
        "question": "What landmark is shown? Describe its key features.",
        "type": "landmark",
    },
    {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Collage_of_Nine_Dogs.jpg/640px-Collage_of_Nine_Dogs.jpg",
        "question": "How many dogs do you see? What breeds can you identify?",
        "type": "counting",
    },
]


# Load model

def load_vlm(model_path: str = VLM_MODEL):
    print(f"Loading {model_path}...")
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_path, torch_dtype=torch.bfloat16, device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(model_path)
    vram = torch.cuda.memory_allocated() / 1e9
    print(f"  VRAM: {vram:.2f} GB")
    return model, processor


def load_image(source: str) -> Image.Image:
    if source.startswith("http"):
        return Image.open(requests.get(source, stream=True, timeout=10).raw).convert("RGB")
    return Image.open(source).convert("RGB")


# Inference

@torch.no_grad()
def vlm_generate(model, processor, image: Image.Image, question: str, max_new_tokens: int = 200) -> str:
    messages = [{"role": "user", "content": [
        {"type": "image", "image": image},
        {"type": "text", "text": question},
    ]}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], images=[image], return_tensors="pt").to("cuda")
    out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    return processor.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


# Part A: Probe base model

def part_probe() -> None:
    print("PART A — Probe base VLM on 5 image types")
    print("Note: Replace TEST_IMAGES with your own domain images for real value.\n")

    model, processor = load_vlm()
    results = []

    for img_info in TEST_IMAGES:
        print(f"\n  Type: {img_info['type']}")
        print(f"  Q: {img_info['question']}")
        try:
            image = load_image(img_info["url"])
            response = vlm_generate(model, processor, image, img_info["question"])
            print(f"  A: {response[:200].strip()}")
            results.append({**img_info, "response": response, "error": None})
        except Exception as e:
            print(f"  Error: {e}")
            results.append({**img_info, "response": None, "error": str(e)})

    out = RESULTS_DIR / "day10_probe.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved → {out}")
    print("\nKey observation: note where the base model fails or hallucinate.")
    print("Those failure cases define what your domain fine-tuning should fix.")


# Part B: Prepare fine-tuning data

def part_prep_data() -> None:
    """
    Scaffold for preparing a VLM fine-tuning dataset.
    LLaMA-Factory expects a specific JSON format.
    This generates example entries — replace with your own images + QA pairs.
    """
    print("PART B — Prepare VLM fine-tuning dataset")

    # LLaMA-Factory VLM dataset format
    dataset = [
        {
            "messages": [
                {
                    "role": "user",
                    "content": "<image>What do you see in this image?",
                },
                {
                    "role": "assistant",
                    "content": "This is a sample response for a domain-specific image.",
                },
            ],
            "images": ["path/to/your/image1.jpg"],
        },
        # Add more examples here
        # Each entry: messages list + images list (parallel)
    ]

    ds_path = DATA_DIR / "vlm_dataset.json"
    ds_path.write_text(json.dumps(dataset, indent=2))
    print(f"Sample dataset written → {ds_path}")
    print("\nTo use your own images:")
    print("  1. Collect 100+ (image, question, answer) triples from your domain")
    print("  2. Format each as the JSON structure above")
    print("  3. Replace 'path/to/your/image1.jpg' with actual paths")

    # Generate LLaMA-Factory config
    config = {
        "model_name_or_path": VLM_MODEL,
        "finetuning_type": "lora",
        "lora_target": "all",
        "lora_rank": 64,
        "lora_alpha": 128,
        "dataset": "vlm_dataset",
        "dataset_dir": str(DATA_DIR),
        "template": "qwen2_vl",
        "output_dir": str(CHECKPOINT_DIR / "vlm_lora"),
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 4,
        "num_train_epochs": 3,
        "learning_rate": 2e-4,
        "bf16": True,
        "gradient_checkpointing": True,
        "report_to": "none",
    }

    cfg_path = CHECKPOINT_DIR / "vlm_lora_config.yaml"
    import yaml
    cfg_path.write_text(yaml.dump(config, default_flow_style=False))
    print(f"LLaMA-Factory config written → {cfg_path}")
    print("\nTo fine-tune (after populating dataset):")
    print(f"  llamafactory-cli train {cfg_path}")


# Part D: Compare base vs fine-tuned

def part_eval(base_only: bool = True, finetuned_path: str | None = None) -> None:
    print("PART D — Evaluate VLM" + (" (base only)" if base_only else " (base vs fine-tuned)"))

    base_model, processor = load_vlm(VLM_MODEL)
    ft_model = None
    if not base_only and finetuned_path and Path(finetuned_path).exists():
        ft_model, _ = load_vlm(finetuned_path)

    results = []
    for img_info in TEST_IMAGES:
        try:
            image = load_image(img_info["url"])
            base_resp = vlm_generate(base_model, processor, image, img_info["question"])
            row = {"type": img_info["type"], "question": img_info["question"], "base": base_resp}

            print(f"\n  [{img_info['type']}] {img_info['question']}")
            print(f"  Base:  {base_resp[:150].strip()}")

            if ft_model:
                ft_resp = vlm_generate(ft_model, processor, image, img_info["question"])
                row["finetuned"] = ft_resp
                print(f"  FT:    {ft_resp[:150].strip()}")

            results.append(row)
        except Exception as e:
            print(f"  Error: {e}")

    tag = "base_only" if base_only else "compare"
    out = RESULTS_DIR / f"day10_eval_{tag}.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved → {out}")

    vram = torch.cuda.memory_allocated() / 1e9
    print(f"VRAM used: {vram:.2f} GB  (vision encoder + LLM in memory simultaneously)")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["probe", "prep_data", "eval"], required=True)
    parser.add_argument("--base_only", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--finetuned", type=str, default=None)
    args = parser.parse_args()

    if args.part == "probe":
        part_probe()
    elif args.part == "prep_data":
        part_prep_data()
    elif args.part == "eval":
        part_eval(base_only=not args.compare, finetuned_path=args.finetuned)


if __name__ == "__main__":
    main()
