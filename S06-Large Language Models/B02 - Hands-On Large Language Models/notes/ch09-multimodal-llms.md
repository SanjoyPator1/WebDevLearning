# Chapter 9: Multimodal Large Language Models

## Hands-On Large Language Models — Chapter 9

> When a model can see, read, and reason across images and text simultaneously, it stops being a language model and becomes something closer to a thinking partner — this chapter shows exactly how that leap is made.

---

## Table of Contents

1. [What Is Multimodality?](#1-what-is-multimodality)
2. [Transformers for Vision (ViT)](#2-transformers-for-vision-vit)
   - [2a. The Problem: Images Can't Be Tokenized Like Text](#2a-the-problem-images-cant-be-tokenized-like-text)
   - [2b. The Solution: Patch Tokenization](#2b-the-solution-patch-tokenization)
   - [2c. Linear Projection and the \[CLASS\] Token](#2c-linear-projection-and-the-class-token)
   - [2d. Dry-Run: From Pixels to Patch Embedding](#2d-dry-run-from-pixels-to-patch-embedding)
   - [2e. Full ViT Pipeline](#2e-full-vit-pipeline)
   - [2f. Why ViT Works — The Elegant Unification](#2f-why-vit-works--the-elegant-unification)
   - [2g. ViT vs CNNs — The Design Philosophy Debate](#2g-vit-vs-cnns--the-design-philosophy-debate)
3. [Multimodal Embedding Models](#3-multimodal-embedding-models)
   - [3a. The Shared Vector Space Idea](#3a-the-shared-vector-space-idea)
   - [3b. What Cross-Modal Search Looks Like](#3b-what-cross-modal-search-looks-like)
   - [3c. What Cross-Modal Embeddings Enable](#3c-what-cross-modal-embeddings-enable)
4. [CLIP: Connecting Text and Images](#4-clip-connecting-text-and-images)
   - [4a. The Training Data: Image-Caption Pairs](#4a-the-training-data-image-caption-pairs)
   - [4b. The Two Encoders: Text + ViT](#4b-the-two-encoders-text--vit)
   - [4c. Contrastive Learning — The Core Idea](#4c-contrastive-learning--the-core-idea)
   - [4d. The Math: Cosine Similarity + InfoNCE Loss](#4d-the-math-cosine-similarity--infonce-loss)
   - [4e. Dry-Run: Computing the Similarity Matrix for 3 Pairs](#4e-dry-run-computing-the-similarity-matrix-for-3-pairs)
   - [4f. What CLIP Learns to Do](#4f-what-clip-learns-to-do)
   - [4g. OpenCLIP: Hands-On Code Walkthrough](#4g-openclip-hands-on-code-walkthrough)
   - [4h. The 3×3 Similarity Matrix — Reading the Numbers](#4h-the-33-similarity-matrix--reading-the-numbers)
5. [Making Text Generation Models Multimodal](#5-making-text-generation-models-multimodal)
   - [5a. Why Text-Only LLMs Can't See](#5a-why-text-only-llms-cant-see)
   - [5b. The Bridge Problem — Illustrated](#5b-the-bridge-problem--illustrated)
   - [5c. Three Strategies for Bridging the Gap](#5c-three-strategies-for-bridging-the-gap)
6. [BLIP-2: Bridging the Modality Gap](#6-blip-2-bridging-the-modality-gap)
   - [6a. The Big Idea — Don't Retrain, Build a Bridge](#6a-the-big-idea--dont-retrain-build-a-bridge)
   - [6b. The Q-Former Architecture](#6b-the-q-former-architecture)
   - [6c. Learnable Query Embeddings — What Are They?](#6c-learnable-query-embeddings--what-are-they)
   - [6d. Dry-Run: Q-Former Cross-Attention with Tiny Numbers](#6d-dry-run-q-former-cross-attention-with-tiny-numbers)
   - [6e. Stage 1: Representation Learning — Three Joint Tasks](#6e-stage-1-representation-learning--three-joint-tasks)
   - [6f. Stage 2: Vision-to-Language — Soft Visual Prompts](#6f-stage-2-vision-to-language--soft-visual-prompts)
   - [6g. Full BLIP-2 Pipeline Diagram](#6g-full-blip-2-pipeline-diagram)
   - [6h. LLaVA and Idefics 2 — The Same Idea, Different Variants](#6h-llava-and-idefics-2--the-same-idea-different-variants)
7. [BLIP-2 in Practice: Preprocessing Multimodal Inputs](#7-blip-2-in-practice-preprocessing-multimodal-inputs)
   - [7a. The Processor — Like a Tokenizer for Images + Text](#7a-the-processor--like-a-tokenizer-for-images--text)
   - [7b. Image Preprocessing: Any Size → 224×224](#7b-image-preprocessing-any-size--224224)
   - [7c. Text Preprocessing: GPT2Tokenizer Quirks](#7c-text-preprocessing-gpt2tokenizer-quirks)
8. [Use Case 1 — Image Captioning](#8-use-case-1--image-captioning)
   - [8a. How It Works End-to-End](#8a-how-it-works-end-to-end)
   - [8b. Code Walkthrough](#8b-code-walkthrough)
   - [8c. Limitations](#8c-limitations)
9. [Use Case 2 — Multimodal Chat-Based Prompting](#9-use-case-2--multimodal-chat-based-prompting)
   - [9a. Visual Question Answering](#9a-visual-question-answering)
   - [9b. Chat-Like Memory Prompting](#9b-chat-like-memory-prompting)
   - [9c. Building an Interactive Chatbot with ipywidgets](#9c-building-an-interactive-chatbot-with-ipywidgets)
10. [Key Takeaways](#10-key-takeaways)

---

## 1. What Is Multimodality?

When you walk into a room, you do not perceive the world through one sense in isolation. Your eyes register colour, shape, depth, and motion. Your ears pick up voices, ambient sound, rhythm. Your hands feel texture and temperature. And your brain integrates all of these streams — fluidly, automatically, without effort — into a single coherent experience of "being in a room." Language, when you use it to describe that experience, is just one of several modalities your brain is simultaneously processing. For humans, multimodality is the default.

For large language models, text has been the only modality since their inception. "Language model" is not just a label — it is a structural constraint. The architecture was built around sequences of discrete tokens, and until researchers found clever ways to extend it, the model was literally blind to everything outside the text domain. A doctor could type a description of an X-ray, but the model could not see the X-ray itself. A user could describe a meme in words, but the model could not look at the meme and respond to its visual content. The text interface was powerful but fundamentally limiting.

A **modality** is a type of data — text, images, audio, video, sensor readings, 3D point clouds, time-series signals. A model is called **multimodal** when it can accept or produce more than one modality type. But the book makes an important nuance explicit from the start: accepting a modality as input is not the same as generating in that modality. You might build a model that accepts images and text together and produces text output (image + text → text), without ever being able to generate new images. Multimodality describes the interface, not symmetric generation capability in all directions.

The taxonomy of multimodal systems matters because different applications require different input-output combinations. Understanding these combinations upfront helps you pick the right tool.

| Model Type | Input Modalities | Output Modalities | Example Application |
|------------|-----------------|-------------------|---------------------|
| CLIP (embedding) | Image + Text | Embeddings only | Cross-modal search, zero-shot classification |
| BLIP-2 | Image + Text | Text | Visual QA, image captioning, multimodal chat |
| Stable Diffusion | Text | Image | Text-to-image generation |
| Whisper | Audio | Text | Speech transcription |
| GPT-4o | Image + Audio + Text | Image + Audio + Text | Full multimodal assistant |
| LLaVA | Image + Text | Text | Instruction-following about images |

```
                         Multimodal System Taxonomy

    INPUT MODALITIES              MODEL               OUTPUT MODALITIES
    ─────────────────             ─────               ─────────────────
    Text ──────────────┐                         ┌──── Text
    Image ─────────────┤                         ├──── Image
    Audio ─────────────┤──── [Multimodal Model] ──┤──── Audio
    Video ─────────────┤                         ├──── Video
    Sensor data ───────┘                         └──── Actions

    Not all combinations need to be supported simultaneously.
    BLIP-2 takes Image + Text → Text.  Stable Diffusion takes Text → Image.
    "Multimodal" just means more than one modality is involved somewhere.
```

Why does this matter for LLMs specifically? The answer is that vision is the most information-dense modality humans use — a single image communicates far more than a thousand words can describe. Giving a language model the ability to perceive images unlocks entirely new classes of applications: reading medical scans, interpreting charts and graphs, understanding spatial relationships, identifying objects without prior labelling, and having conversations about the visual world. The chapters on CLIP and BLIP-2 show the two main paradigms for achieving this: embedding-based approaches that place images and text in the same vector space, and generation-based approaches that extend a text-only LLM to reason about images via a learned bridge.

---

## 2. Transformers for Vision (ViT)

### 2a. The Problem: Images Can't Be Tokenized Like Text

The original Transformer was built for sequences of discrete tokens. Text fits this model beautifully — words, subwords, or characters are naturally discrete units with a finite vocabulary. You can assign an integer ID to each token and look it up in an embedding table. The whole architecture rests on this foundation.

Images do not have discrete units. An image is a continuous grid of pixel values. A 512×512 RGB image contains 512 × 512 × 3 = 786,432 individual numbers, one for each colour channel of each pixel. If you tried to feed each pixel as a separate token, the self-attention mechanism would need to compute attention scores between every pair of 786,432 tokens. Self-attention scales quadratically with sequence length — that computation is utterly intractable.

The analogy here is powerful: imagine trying to read a book by processing each individual letter, one at a time, and relating every letter to every other letter in the book simultaneously. It would work in theory, but the computational cost would be insane. Readers don't work that way — they see words, phrases, and sentences as units of meaning. The Vision Transformer (ViT) applies exactly this logic: instead of pixels, use *patches*.

### 2b. The Solution: Patch Tokenization

The **Vision Transformer (ViT)**, introduced in the paper *"An Image is Worth 16×16 Words"* (Dosovitskiy et al., 2020), solved the sequencing problem by treating rectangular image patches as tokens. The procedure is simple: take the original image and cut it into a grid of non-overlapping square patches. For a 512×512 image with 16×16 pixel patches, you get 32×32 = 1,024 patches — a manageable sequence length for a Transformer.

Each patch is a 16×16×3 = 768-dimensional vector (width × height × RGB channels). This is the "raw" patch representation. The paper's title is not accidental — 16×16 patches are the exact equivalent of words in a sentence. Just as a sentence of 50 words is processed as a sequence of 50 tokens, an image is now processed as a sequence of 1,024 patch tokens.

```
Original Image (512×512 pixels)
┌─────────────────────────────────┐
│  P1  │  P2  │  P3  │ ... │ P32 │
│──────┼──────┼──────┼─────┼─────│
│  P33 │  P34 │  P35 │ ... │ P64 │
│──────┼──────┼──────┼─────┼─────│
│  ... │  ... │  ... │ ... │ ... │
│──────┼──────┼──────┼─────┼─────│
│P993  │P994  │P995  │ ... │P1024│
└─────────────────────────────────┘
Each patch = 16×16 pixels × 3 channels = 768 raw values

→ After flattening and ordering: a sequence of 1,024 patch vectors
```

For illustrative purposes, the book's diagrams use 3×3 patches (giving 9 patch tokens), which is easier to draw. The actual ViT implementation uses 16×16 patches, which is why it's called "An Image is Worth 16×16 Words."

### 2c. Linear Projection and the \[CLASS\] Token

With text tokens, you can look up an embedding vector in a table by token ID. Patches can't do this — there is no finite vocabulary of patches. Two photos of different cats will produce slightly different pixel values for what is essentially the same patch content. Assigning a discrete ID to each unique patch is impossible.

Instead, ViT performs a **linear projection**: each flattened patch vector (768-dim for 16×16×3 patches) is multiplied by a learned weight matrix $W_p$ to produce a **patch embedding** of size $d_{model}$. This is mathematically identical to the linear projection inside a Transformer's attention head — it is just a matrix multiply. The weights in $W_p$ are learned during training, and the model discovers on its own which low-dimensional representation of each patch is most useful.

$$e_i = \text{flatten}(P_i) \cdot W_p \quad \in \mathbb{R}^{d_{model}}$$

| Symbol | Meaning |
|--------|---------|
| $P_i$ | The $i$-th image patch, a 2D array of pixels |
| $\text{flatten}(P_i)$ | The patch unrolled into a 1D vector |
| $W_p$ | Learnable projection matrix, shape $(patch\_size^2 \times C,\ d_{model})$ |
| $e_i$ | Patch embedding for patch $i$, shape $(d_{model},)$ |

After producing patch embeddings, ViT prepends a special **[CLASS] token** — a learnable vector of dimension $d_{model}$ — to the sequence, just as BERT does for text. This token has no corresponding patch; its job is to accumulate global information about the entire image through attention. After the encoder runs, the [CLASS] token's final representation is used as the image-level embedding for downstream tasks like classification.

Finally, **positional embeddings** are added to each patch embedding (including the [CLASS] token) to give the model information about where in the image each patch came from. Without positional information, a patch from the top-left corner would be indistinguishable from the same patch in the bottom-right corner.

### 2d. Dry-Run: From Pixels to Patch Embedding

Let's walk through the full projection with tiny numbers. We'll use a 4×4 image split into four 2×2 patches, with 1 channel (greyscale), and project down to a 3-dimensional embedding.

```
Setup:
  Image = 4×4 greyscale pixels:
    [[10, 20, 30, 40],
     [50, 60, 70, 80],
     [15, 25, 35, 45],
     [55, 65, 75, 85]]

  Patch size = 2×2, so we get 4 patches (2×2 grid of patches):
    P1 (top-left)     = [[10, 20], [50, 60]]
    P2 (top-right)    = [[30, 40], [70, 80]]
    P3 (bottom-left)  = [[15, 25], [55, 65]]
    P4 (bottom-right) = [[35, 45], [75, 85]]

Step 1: Flatten P1
  flatten(P1) = [10, 20, 50, 60]   ← 4-dimensional vector (2×2×1)

Step 2: Linear Projection   W_p has shape (4, 3) — projects from 4-dim to 3-dim
  (Pretend W_p is learned; for illustration use this toy matrix)
  W_p = [[0.1,  0.0, -0.1],
          [0.0,  0.1,  0.0],
          [0.1,  0.0,  0.1],
          [0.0, -0.1,  0.0]]

Step 3: Compute e1 = flatten(P1) · W_p
  [10, 20, 50, 60] · W_p

  dim 0: 10×0.1 + 20×0.0 + 50×0.1 + 60×0.0 = 1.0 + 0 + 5.0 + 0 = 6.0
  dim 1: 10×0.0 + 20×0.1 + 50×0.0 + 60×(-0.1) = 0 + 2.0 + 0 - 6.0 = -4.0
  dim 2: 10×(-0.1) + 20×0.0 + 50×0.1 + 60×0.0 = -1.0 + 0 + 5.0 + 0 = 4.0

  → e1 = [6.0, -4.0, 4.0]  ← 3-dimensional patch embedding for patch P1

Step 4: Repeat for P2, P3, P4 to get e2, e3, e4.

Step 5: Prepend [CLASS] token (a learnable 3-dim vector, e.g. [0.0, 0.0, 0.0] at init)
  Sequence fed to encoder: [[CLS], e1, e2, e3, e4]
  = [[0,0,0], [6,-4,4], ...]   ← 5 tokens, each 3-dimensional

Step 6: Add positional embeddings (one per position, also 3-dim, learned)
  Then pass this 5-token sequence into a standard Transformer encoder.
```

*Interpretation:* The projection matrix $W_p$ learned to collapse the 4 pixel values of each 2×2 patch into a 3-dimensional representation that the Transformer can reason about. The encoder then runs exactly as it would for text — no special modifications.

### 2e. Full ViT Pipeline

```
Original Image (e.g. 512×512 RGB)
          │
          ▼  cut into non-overlapping patches
  ┌───┬───┬───┐
  │P1 │P2 │P3 │
  ├───┼───┼───┤   → N patches, each = (patch_size² × channels) raw values
  │P4 │P5 │P6 │
  ├───┼───┼───┤
  │P7 │P8 │P9 │
  └───┴───┴───┘
          │ flatten each patch
          ▼
  [flat_P1][flat_P2]...[flat_PN]    shape: (N, patch_size²×C)
          │
          ▼  linear projection  W_p
  [e1][e2]...[eN]                   shape: (N, d_model)
          │
          ▼  prepend [CLASS] token
  [[CLS]][e1][e2]...[eN]            shape: (N+1, d_model)
          │
          ▼  add positional embeddings  (learned, one per position)
  [[CLS]+pos0][e1+pos1]...[eN+posN]
          │
          ▼
     ┌─────────────────────┐
     │  Transformer ENCODER│  ← identical to BERT encoder
     │  (self-attention +  │     no architectural changes
     │   FFN, repeated L×) │
     └─────────────────────┘
          │
          ▼
  Output representations: one vector per token
  [cls_out][patch_out_1]...[patch_out_N]
          │
  [cls_out] ──► classification head (for image classification tasks)
  all outputs ──► downstream multimodal tasks (CLIP, BLIP-2)
```

### 2f. Why ViT Works — The Elegant Unification

The profound insight of ViT is that from the moment patch embeddings enter the encoder, they are **completely indistinguishable from text token embeddings**. The Transformer encoder does not know or care whether its input came from pixels or words. It simply sees a sequence of $d_{model}$-dimensional vectors with positional information and runs its attention and feed-forward layers. The architecture is identical to BERT.

This means all the things that make Transformers powerful — long-range dependencies through attention, pre-training on massive datasets, transfer learning — apply directly to images. You pre-train ViT on a large image classification dataset (ImageNet, JFT-300M), and then fine-tune it on downstream tasks, exactly as you would fine-tune BERT for NLP. The analogy is so tight that the ViT paper literally calls it "An Image is Worth 16×16 Words" — because that is precisely what it does.

This elegant unification is what makes ViT the default image encoder in virtually all modern multimodal systems, including CLIP and BLIP-2.

### 2g. ViT vs CNNs — The Design Philosophy Debate

When the ViT paper appeared in 2020, it was deliberately provocative. Convolutional Neural Networks (CNNs) had dominated computer vision for nearly a decade — from AlexNet (2012) to ResNet (2015) to EfficientNet (2019). ViT challenged the assumption that convolution was the right inductive bias for vision. The debate is worth understanding because it reveals what makes ViT uniquely suited for multimodal systems.

CNNs encode two strong architectural assumptions: **locality** (nearby pixels are more related than distant pixels, so convolutions use small local windows) and **translation invariance** (the same feature detector should work anywhere in the image, so filters are shared across positions). These assumptions are correct for many natural images, which is why CNNs trained efficiently on relatively small datasets. But they are *assumptions* — they are baked into the architecture regardless of the actual image content.

ViT makes no such assumptions. Self-attention can relate any patch to any other patch, regardless of spatial distance. Whether two patches are adjacent or at opposite corners of the image makes no difference to the attention mechanism — both pairs receive equal treatment. The model learns from data which patches to relate to which, without geometric constraints. This is more flexible, but it comes at a cost: ViT requires significantly more training data to learn useful representations from scratch, because it cannot rely on the locality bias that CNNs benefit from.

| Aspect | CNN | ViT |
|--------|-----|-----|
| Core operation | Convolution (local windows) | Self-attention (global, all pairs) |
| Spatial assumption | Local features matter most | No assumption — learns from data |
| Translation invariance | Built-in (shared filters) | Must be learned or added |
| Data efficiency | High — works on small datasets | Low — needs large datasets |
| Long-range dependencies | Requires deep stacking | Captured in every layer |
| Pre-training data needed | ~1M images (ImageNet) | ~14M–300M images (JFT) |
| Scalability | Diminishing returns with scale | Keeps improving with more data |
| Used in multimodal systems | Rarely (old CLIP variants) | Yes — dominant choice |

The resolution to the debate came through scale. When ViT is pre-trained on sufficiently large datasets — JFT-300M or internet-scale image-caption pairs — its lack of inductive bias becomes a strength: it is less constrained and learns richer, more transferable representations. For multimodal systems in particular, the ability to represent the entire image as a flat sequence of patch embeddings, in exactly the same format as text token embeddings, makes ViT the only practical choice. CNNs produce feature maps with spatial dimensions that do not map cleanly onto the 1D sequences that Transformers expect.

---

## 3. Multimodal Embedding Models

### 3a. The Shared Vector Space Idea

Imagine a GPS coordinate system for meaning. In geographic space, every location on Earth has a latitude and longitude — two numbers that uniquely identify a point. Nearby coordinates correspond to nearby places: Paris (48.85°N, 2.35°E) is close to Brussels (50.85°N, 4.35°E) but far from Tokyo (35.68°N, 139.69°E). The coordinate system is universal: it does not matter whether a location is a city, a mountain, or an ocean — everything gets the same kind of coordinate.

**Multimodal embedding models** build the equivalent for meaning. Instead of two numbers, they use 512 or 768-dimensional coordinates. Instead of geographic proximity, proximity in this space encodes semantic relatedness. The revolutionary extension that makes these models multimodal is that the coordinate system is *universal across modalities*: a photograph of a cat and the sentence "a fluffy grey kitten" are assigned nearby coordinates, even though one is a pixel array and the other is a sequence of tokens. The embedding model has learned to project both modalities onto the same semantic map.

Recall from earlier chapters that text-only embedding models (like SBERT) already create these high-dimensional coordinate maps for text. What multimodal models add is the ability to place images on the *same* map — not a separate map for images and a separate map for text, but one unified space where cross-modal comparisons are geometrically meaningful.

This is not trivial to achieve. The two modalities have completely different raw representations — one is floating-point pixel values, the other is discrete token IDs. Bringing them into the same space requires training a model to align their meanings, and this alignment is learned entirely from data: millions of image-caption pairs where humans naturally describe what they see.

### 3b. What Cross-Modal Search Looks Like

Once images and text share a vector space, entirely new operations become possible. The search mechanism is identical to the dense retrieval described in earlier chapters — you are simply querying across modalities rather than within one.

```
Shared Embedding Space (2D projection for illustration)
                                              dim 1
                                                │
                                                │
  "My cat is cute"  ●──────● [cat photo]        │
                                                │
                                                │
    "A puppy in snow" ●────────● [puppy photo]  │
                                                │
    "A supercar at sunset"  ●──────────────────●│[car photo]
  ─────────────────────────────────────────────┼─────── dim 0
                                                │
  Road ●                   "Snowing" ●          │
                                                │
                   "I love dogs" ●              │
                                                │

  Text and image embeddings coexist in the same space.
  Proximity = semantic similarity, regardless of modality.
```

Given a text query "pictures of a puppy," you embed that query and find all image vectors closest to it — this is **text-to-image search**. Conversely, embed an image and find all text captions or documents nearest to it — this is **image-to-text search**. The retrieval algorithm (approximate nearest neighbour lookup in a vector database) is completely modality-agnostic; it only sees distance in the shared space.

### 3c. What Cross-Modal Embeddings Enable

The shared vector space unlocks a wide range of applications that were impossible with text-only or vision-only systems.

| Use Case | Query Modality | Database Modality | Example |
|----------|---------------|-------------------|---------|
| Text-to-image search | Text | Images | "Find me photos of red sunsets" |
| Image-to-text search | Image | Text/captions | Upload a product photo → find matching descriptions |
| Zero-shot classification | Image | Class label texts | Is this image a cat, dog, or car? (no training examples needed) |
| Cross-modal clustering | Images + Text | Mixed | Group travel photos with their matching blog excerpts |
| Image generation conditioning | Text | — | Stable Diffusion uses CLIP text embeddings to guide generation |
| Duplicate detection | Image | Images | Find near-identical images even after colour correction |

The crucial insight — and why the rest of this chapter matters — is that **CLIP** is the specific model that learned to create this shared space at scale. Every downstream use case listed above, from zero-shot classification to Stable Diffusion, runs on top of CLIP embeddings. Understanding how CLIP works is therefore understanding the foundation of modern multimodal AI.

---

## 4. CLIP: Connecting Text and Images

### 4a. The Training Data: Image-Caption Pairs

**CLIP** (Contrastive Language–Image Pre-training), introduced by OpenAI in 2021, is trained on a dataset of 400 million image-caption pairs collected from the internet. Each pair consists of an image and a natural language caption that describes that image — the kind of alt-text, captions, and annotations that appear naturally across the web.

The key structure of this dataset is: each image-caption pair is a **positive example** (they match), and all other combinations of images and captions within a training batch are **negative examples** (they don't match). In a batch of 256 image-caption pairs, there are 256 positive pairs and 256×256 - 256 = 65,280 negative pairs. The sheer density of negative supervision makes the training signal very rich.

### 4b. The Two Encoders: Text + ViT

CLIP uses two separate encoders that are trained simultaneously:

```
        Image                           Text
   [Puppy photo]                  "A puppy playing in the snow"
         │                                    │
         ▼                                    ▼
  ┌─────────────┐                    ┌──────────────────┐
  │ Image Encoder│                   │  Text Encoder    │
  │    (ViT)    │                   │  (Transformer)   │
  └─────────────┘                   └──────────────────┘
         │                                    │
         ▼                                    ▼
  image_embedding                    text_embedding
  shape: (512,)                      shape: (512,)
         │                                    │
         └────────────────────────────────────┘
                          │
                   cosine_similarity(image_embedding, text_embedding)
                          │
                   training signal: should be HIGH for this matched pair
```

Both encoders project their respective inputs into the same 512-dimensional space. The image encoder is a ViT; the text encoder is a BERT-like Transformer. After training, the embedding of "a puppy playing in the snow" and the embedding of an actual photo of a puppy in the snow will be geometrically close in this shared 512-dimensional space.

### 4c. Contrastive Learning — The Core Idea

The training method is called **contrastive learning**, and it is one of the most elegant ideas in modern machine learning. The intuition is this: you have matched pairs (positive examples) and unmatched pairs (negative examples). You want to train the model so that the embeddings of matched pairs are pulled *together* in vector space, while the embeddings of unmatched pairs are pushed *apart*.

Imagine a physics simulation. Matched pairs are connected by a spring that pulls them toward each other. Unmatched pairs are connected by a repulsive force that pushes them away. Over millions of training steps, the embedding space organises itself so that semantically related things cluster together, regardless of their modality.

A more concrete analogy: think of a language school where students are paired with native speakers. If a student says "chien" and their French partner shows them a photo of a dog, the pairing is positive — they should learn to associate these. If the student says "chien" but the partner shows them a photo of a car, that's a negative pair — a deliberate contrast that teaches the model what is *not* a match. Over millions of such pairings, the model learns a rich understanding of correspondence between language and vision.

The critical detail is that negative pairs are generated automatically within each batch. For a batch of $N$ image-caption pairs, you have $N$ positives along the diagonal of an $N \times N$ similarity matrix, and $N^2 - N$ negatives everywhere else. The model must learn to make the diagonal the brightest part of that matrix.

### 4d. The Math: Cosine Similarity + InfoNCE Loss

**Cosine similarity** measures how aligned two vectors are, independent of their magnitude:

$$\text{sim}(u, v) = \frac{u \cdot v}{\|u\| \cdot \|v\|}$$

| Symbol | Meaning |
|--------|---------|
| $u, v$ | Two embedding vectors (e.g. image embedding and text embedding) |
| $u \cdot v$ | Dot product — sum of elementwise products |
| $\|u\|$ | L2 norm (Euclidean length) of vector $u$ |
| $\text{sim}(u,v)$ | Range: $[-1, 1]$. Value of 1 = perfectly aligned, 0 = orthogonal, -1 = opposite |

When embeddings are L2-normalised (each vector divided by its length to have unit norm), cosine similarity reduces to a simple dot product: $\text{sim}(u,v) = u \cdot v$. This is why CLIP normalises embeddings before computing similarities.

The training objective is the **InfoNCE loss** (also called NT-Xent in some formulations). For a batch of $N$ image-caption pairs, the loss encourages the model to identify the correct image for each text query and the correct text for each image query — simultaneously:

$$\mathcal{L} = -\frac{1}{2N}\sum_{i=1}^{N} \left[ \log \frac{e^{\text{sim}(t_i,\, v_i)/\tau}}{\sum_{j=1}^{N} e^{\text{sim}(t_i,\, v_j)/\tau}} + \log \frac{e^{\text{sim}(v_i,\, t_i)/\tau}}{\sum_{j=1}^{N} e^{\text{sim}(v_i,\, t_j)/\tau}} \right]$$

| Symbol | Meaning |
|--------|---------|
| $t_i$ | Text embedding for the $i$-th caption |
| $v_i$ | Image (visual) embedding for the $i$-th image |
| $\tau$ | Temperature — a learned scalar that controls the sharpness of the distribution |
| $N$ | Batch size — number of image-caption pairs in this training step |
| $\log(\cdot)$ | Natural logarithm — converting softmax probabilities into a loss |

*This says:* For each text embedding $t_i$, compute its similarity against all $N$ image embeddings, apply softmax (the denominator), and take the log-probability assigned to the correct match (the numerator). The loss is the negative log of this probability — minimising it forces the model to assign high probability to the correct pair. The factor of $\frac{1}{2}$ averages the text-to-image and image-to-text directions.

*Intuition for temperature $\tau$:* A small $\tau$ (e.g. 0.07) makes the softmax very sharp — the model must be very confident. A large $\tau$ makes the distribution flat, giving a softer gradient signal. Temperature is typically a learnable parameter in CLIP.

### 4e. Dry-Run: Computing the Similarity Matrix for 3 Pairs

Let's compute the full similarity matrix for a batch of 3 image-caption pairs using 2-dimensional (already L2-normalised) embeddings.

```
Setup — 3 image-caption pairs, 2D embeddings (already unit-norm):

  image_puppy  = [0.90,  0.44]   ← normalised so ‖v‖ = 1
  image_cat    = [0.10,  0.99]
  image_car    = [0.71, -0.71]

  text_puppy   = [0.85,  0.53]
  text_cat     = [0.05,  1.00]  (≈ normalised)
  text_car     = [0.71, -0.70]

Step 1: Build the 3×3 similarity matrix S where S[i,j] = text_i · image_j

  S[0,0] = text_puppy · image_puppy = 0.85×0.90 + 0.53×0.44 = 0.765 + 0.233 = 0.998  ✓ diagonal
  S[0,1] = text_puppy · image_cat   = 0.85×0.10 + 0.53×0.99 = 0.085 + 0.525 = 0.610
  S[0,2] = text_puppy · image_car   = 0.85×0.71 + 0.53×(-0.71) = 0.604 - 0.376 = 0.228

  S[1,0] = text_cat · image_puppy   = 0.05×0.90 + 1.00×0.44 = 0.045 + 0.440 = 0.485
  S[1,1] = text_cat · image_cat     = 0.05×0.10 + 1.00×0.99 = 0.005 + 0.990 = 0.995  ✓ diagonal
  S[1,2] = text_cat · image_car     = 0.05×0.71 + 1.00×(-0.71) = 0.035 - 0.710 = -0.675

  S[2,0] = text_car · image_puppy   = 0.71×0.90 + (-0.70)×0.44 = 0.639 - 0.308 = 0.331
  S[2,1] = text_car · image_cat     = 0.71×0.10 + (-0.70)×0.99 = 0.071 - 0.693 = -0.622
  S[2,2] = text_car · image_car     = 0.71×0.71 + (-0.70)×(-0.71) = 0.504 + 0.497 = 1.001 ≈ 1.0 ✓

Similarity matrix S (rows = text, cols = image):
              image_puppy  image_cat  image_car
  text_puppy  [  0.998       0.610      0.228  ]
  text_cat    [  0.485       0.995     -0.675  ]
  text_car    [  0.331      -0.622      1.001  ]

Step 2: Apply softmax to row 0 (text_puppy vs. all images), with τ = 0.07
  Scaled scores: [0.998/0.07, 0.610/0.07, 0.228/0.07]
               = [14.26,      8.71,        3.26]

  exp values:  e^14.26 ≈ 1,561,000    e^8.71 ≈ 6,071    e^3.26 ≈ 26.1
  sum = 1,567,097

  softmax row 0 ≈ [1561000/1567097, 6071/1567097, 26.1/1567097]
               ≈ [0.9961,           0.0039,        0.000017]

Step 3: Compute loss contribution for text_puppy
  Loss_0 = -log(0.9961) ≈ 0.004  ← very small because correct pair is confident

Step 4: For a random (untrained) model with near-zero similarity scores,
  the softmax would be ≈ [0.33, 0.33, 0.33], giving loss ≈ -log(0.33) ≈ 1.1

Interpretation:
  → The diagonal entries are highest in our toy example — a perfectly trained CLIP
    would produce a near-identity similarity matrix (diagonal = 1, off-diagonal = 0).
  → Low temperature (τ=0.07) makes the softmax very sharp — the model MUST be confident.
  → The contrastive loss drives all three diagonal entries toward 1.0 simultaneously.
```

### 4f. What CLIP Learns to Do

After training, CLIP is remarkably general. The shared embedding space enables several capabilities that require no additional training:

**Zero-shot image classification** works by embedding an image and also embedding text descriptions of candidate classes ("a photo of a dog," "a photo of a cat," "a photo of a car"). The class whose text embedding is closest to the image embedding wins. This means CLIP can classify images into any category you can describe in text, without ever having seen labelled examples of that category.

**Cross-modal search** lets you retrieve images from a database using a text query, or retrieve documents using an image query. The mechanism is identical to dense retrieval — you are just querying across modalities.

**Image clustering** works by computing image embeddings and running k-means or HDBSCAN in the shared space. Because the space is semantically structured, the clusters that emerge correspond to meaningful visual categories — even if those categories were never explicitly labelled in the training data.

**Generative applications** use CLIP embeddings to guide image generation. Stable Diffusion, for example, uses CLIP text embeddings as the conditioning signal that tells the diffusion model what image to generate. This is why Stable Diffusion responds so richly to natural language prompts.

| CLIP Use Case | How It Works | Requires Fine-Tuning? |
|---------------|--------------|----------------------|
| Zero-shot classification | Embed image + class label texts, find nearest text | No |
| Text-to-image search | Embed text query, ANN search over image embeddings | No |
| Image-to-text search | Embed image, ANN search over text embeddings | No |
| Image clustering | Embed images, run clustering in shared space | No |
| Stable Diffusion conditioning | Use text embedding as generation condition | No (just inference) |
| Domain-specific search | Same as above but on custom dataset | Fine-tune optional |

### 4g. OpenCLIP: Hands-On Code Walkthrough

**OpenCLIP** is the open-source implementation of CLIP. Working with any CLIP model boils down to three components: a tokenizer (for text), a preprocessor (for images), and the main model.

```python
from transformers import CLIPTokenizerFast, CLIPProcessor, CLIPModel

model_id = "openai/clip-vit-base-patch32"

# Tokenizer — converts text to token IDs
clip_tokenizer = CLIPTokenizerFast.from_pretrained(model_id)

# Processor — resizes and normalises images to the model's expected format
clip_processor = CLIPProcessor.from_pretrained(model_id)

# Main model — contains both text encoder and image encoder (ViT)
model = CLIPModel.from_pretrained(model_id)
```

**Processing text and generating a text embedding:**

```python
caption = "a puppy playing in the snow"

# Tokenize — converts text to token IDs and attention mask
inputs = clip_tokenizer(caption, return_tensors="pt")
# inputs["input_ids"] → tensor of token IDs
# inputs["attention_mask"] → tensor of 1s (all tokens attended to)

# Generate text embedding
text_embedding = model.get_text_features(**inputs)
print(text_embedding.shape)  # torch.Size([1, 512])
# One embedding vector of 512 dimensions for the entire caption
```

**Processing an image and generating an image embedding:**

```python
# Preprocess — resizes image to 224×224, normalises pixel values
processed_image = clip_processor(text=None, images=image, return_tensors="pt")["pixel_values"]
print(processed_image.shape)  # torch.Size([1, 3, 224, 224])
# batch=1, channels=3 (RGB), height=224, width=224

image_embedding = model.get_image_features(processed_image)
print(image_embedding.shape)  # torch.Size([1, 512])
# Same shape as text_embedding — this is the key!
```

**Computing similarity between the two embeddings:**

```python
# Normalise to unit vectors so dot product = cosine similarity
text_embedding  /= text_embedding.norm(dim=-1, keepdim=True)
image_embedding /= image_embedding.norm(dim=-1, keepdim=True)

# Convert to numpy and compute dot product
t_emb = text_embedding.detach().cpu().numpy()
i_emb = image_embedding.detach().cpu().numpy()
score = np.dot(t_emb, i_emb.T)
# score ≈ 0.33 for matched puppy image and caption
```

The fact that `text_embedding.shape == image_embedding.shape == [1, 512]` is the entire point — both modalities live in the same space, enabling direct comparison.

An easier alternative using `sentence-transformers`:

```python
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("clip-ViT-B-32")

image_embeddings = model.encode(images)   # list of PIL images
text_embeddings  = model.encode(captions) # list of strings

sim_matrix = util.cos_sim(image_embeddings, text_embeddings)
```

### 4h. The 3×3 Similarity Matrix — Reading the Numbers

When you run CLIP on 3 image-caption pairs from the book, you get the following similarity matrix (rows = captions, columns = images):

|  | Puppy photo | Cat photo | Car photo |
|---|---|---|---|
| "A puppy playing in the snow" | **0.33** | 0.19 | 0.11 |
| "A pixelated image of a cute cat" | 0.15 | **0.35** | 0.09 |
| "A supercar on the road with sunset in background" | 0.08 | 0.13 | **0.31** |

The diagonal entries (bold) are highest in each row — CLIP correctly identifies which caption matches which image. The score of 0.33 for the puppy pair looks small in isolation, but comparing it to 0.19 and 0.11 shows it is the dominant signal. This relative interpretation is what matters — cosine similarity scores are not absolute; their meaning comes from comparison within the same embedding space.

---

## 5. Making Text Generation Models Multimodal

### 5a. Why Text-Only LLMs Can't See

Text generation models like GPT or LLaMA are fundamentally text machines. Their input layer accepts a sequence of token IDs — integers that index into a vocabulary of ~50,000 entries. The forward pass converts each integer into an embedding vector via a lookup table, then passes those vectors through the Transformer. The entire pipeline is built around discrete tokens.

An image has no such discrete representation. You cannot express a photograph as a sequence of vocabulary indices. The scale alone illustrates the problem: a 512×512 RGB image contains 512 × 512 × 3 = **786,432** individual pixel values, each in the range 0–255. Even if you tried to treat each pixel value as a token ID, you would need a vocabulary that extends to 255 — which does overlap with the LLM's vocabulary, but the mapping would be completely meaningless. Vocabulary index 127 in a language model corresponds to a specific subword or character (perhaps the word "the" or the character `m`) — it has nothing to do with the pixel brightness value 127. The model has no learned association between pixel intensities and language concepts.

```
Image (512×512 RGB)                   Text ("A red car")
────────────────────                  ──────────────────
pixel values:                         token IDs:
[127, 255, 63, 89, 200, ...]         [1045, 318, 1097]
       │                                     │
       ✗ Cannot feed directly                ✓ Vocabulary lookup
       │                                     │
       ▼                                     ▼
Pixel 127 as "token"?           token 1045 → embedding["A"]
→ embedding[127] = "the"        token 318  → embedding["red"]
→ WRONG — pixel ≠ word ID       token 1097 → embedding["car"]
                                (all correct, semantically grounded)

786,432 pixel values
→ ~15× longer than the typical context window (50K tokens)
→ Values 0–255 overlap with real token IDs but carry no language meaning
→ The LLM has zero knowledge connecting pixel intensity to visual semantics
```

This is the **modality gap**: two powerful systems that both operate on sequences of vectors, but whose vector spaces are semantically incompatible. A ViT's image embeddings live in the visual representation space; an LLM's token embeddings live in the linguistic representation space. Bridging these spaces is the central challenge of multimodal language model design.

### 5b. The Bridge Problem — Illustrated

Think of a brilliant scholar who has been blind since birth. Over decades of reading, they have built an extraordinary mental model of the world through language — they understand colour theory from physics papers, can discuss Renaissance painting from written descriptions, and can reason about architectural space from text. Now you want to give them sight. You don't rebuild their entire brain — decades of linguistic knowledge are invaluable and shouldn't be discarded. Instead, you train a dedicated *visual interpreter*: a companion who observes the visual scene and communicates it in the scholar's native language. The scholar's underlying intelligence (the LLM) stays intact. Only the interpreter (the bridge module) needs to be trained.

This analogy captures BLIP-2 almost exactly. The "scholar" is the frozen LLM; the "companion" is the Q-Former. The Q-Former watches the image (via the frozen ViT), distils the most important visual information into a compact representation, and presents that representation to the LLM in the form it already understands — sequences of embedding vectors.

```
The Bridge Problem:

ViT output                 Bridge Module             LLM input
─────────────              ────────────              ─────────
[patch_1_vec]              learns to               [soft_v1]
[patch_2_vec]   ──────►   translate   ──────►     [soft_v2]
[patch_3_vec]              visual to              [soft_v3]
    ...                    linguistic               ...
[patch_N_vec]              representation          [soft_v32]  [text tokens...]
                                                      │
                                                      ▼
                                               Frozen LLM generates text
                                               conditioned on both
                                               visual and text context
```

The bridge must solve two problems simultaneously. First, it must compress the ViT's output (hundreds of patch vectors) into a much smaller representation that the LLM's context window can accommodate. Second, it must project this compressed representation into the LLM's embedding space, so the LLM can process it with the same attention mechanisms it uses for text tokens.

### 5c. Three Strategies for Bridging the Gap

Researchers have explored several architectures for building this bridge. The three most important approaches differ in their complexity, compute cost, and the quality of visual-language alignment they achieve.

**Strategy 1 — Linear Projection (LLaVA):** The simplest possible bridge is a single trainable linear layer. CLIP (or any ViT) produces image embeddings; a linear projection matrix maps those embeddings directly into the LLM's embedding dimension. LLaVA compensates for this architectural simplicity with a richer training procedure: instead of image-caption pairs, it trains on instruction-following conversations about images (generated by GPT-4), which teaches the LLM to be conversational about visual content.

**Strategy 2 — Q-Former (BLIP-2):** A full trainable Transformer module sits between the ViT and the LLM. A fixed set of 32 learnable query vectors cross-attend to the ViT's patch features, extracting and compressing visual information. The Q-Former is trained in two stages: first to align visual and textual representations, then to generate soft visual prompts for the LLM. More complex than LLaVA but produces richer visual representations.

**Strategy 3 — Cross-Attention Integration (Flamingo):** Rather than projecting vision into the LLM's input sequence, Flamingo inserts new cross-attention layers *inside* every Transformer block of the LLM. These layers allow the LLM to attend to visual features at every layer of processing, not just at the input. This is the most deeply integrated approach but requires modifying the LLM architecture and training all the new cross-attention layers.

| Strategy | Complexity | Training Cost | Visual-Language Depth | Representative Model |
|----------|-----------|--------------|----------------------|----------------------|
| Linear Projection | Low | Low | Shallow — single mapping | LLaVA |
| Q-Former Bridge | Medium | Medium | Deep — multi-task alignment | BLIP-2 |
| Cross-Attention Integration | High | High | Deepest — vision at every layer | Flamingo, Idefics |

*Rule of thumb:* If you want the simplest implementation with strong instruction-following, choose LLaVA-style projection. If you want rich visual understanding with moderate compute, choose BLIP-2. If you want the deepest integration and have significant compute, choose Flamingo-style cross-attention.

---

## 6. BLIP-2: Bridging the Modality Gap

### 6a. The Big Idea — Don't Retrain, Build a Bridge

**BLIP-2** (Bootstrapping Language-Image Pre-training for Unified Vision-Language Understanding and Generation 2) was introduced by Salesforce Research in 2023. Its central insight is resource efficiency: training a multimodal model from scratch requires billions of image-text pairs and enormous compute. But we already have excellent pretrained models — ViT for vision and large language models like OPT or FlanT5 for text. Why not freeze both and train only a lightweight bridge between them?

BLIP-2's answer is the **Q-Former** (Querying Transformer) — a small, trainable module that acts as an adapter between a frozen image encoder (ViT) and a frozen LLM. The ViT and the LLM never have their weights updated. Only the Q-Former, which is far smaller, is trained. This dramatically reduces the compute cost and data requirements.

```
Frozen ViT         Trainable Q-Former         Frozen LLM
(vision expert)    (the bridge)               (language expert)

    [❄]        →        [🔥]          →           [❄]
 stays fixed      learns to translate          stays fixed
```

### 6b. The Q-Former Architecture

The Q-Former is architecturally a Transformer, but it has a unique design: two sub-modules that **share their self-attention layers** while having separate cross-attention layers:

```
                        Q-Former
          ┌─────────────────────────────────────┐
          │                                     │
          │   ┌───────────────────────────┐     │
          │   │   Image Transformer       │     │
          │   │  (cross-attention to ViT) │     │
          │   └─────────┬─────────────────┘     │
          │             │ shared self-attention  │
          │   ┌─────────┴─────────────────┐     │
          │   │   Text Transformer        │     │
          │   │  (interacts with LLM text)│     │
          │   └───────────────────────────┘     │
          │                                     │
          │   Learnable Query Embeddings         │
          │   [Q1][Q2]...[Q32]                  │
          └─────────────────────────────────────┘
```

The **Image Transformer** component cross-attends to the frozen ViT's output features — it "looks at" the image through the frozen encoder. The **Text Transformer** component processes text (captions during training, questions during inference) and can eventually interact with the LLM. Both modules share their self-attention layers, meaning the 32 learnable query embeddings can attend to both image features and text simultaneously.

### 6c. Learnable Query Embeddings — What Are They?

The most unusual part of Q-Former is its **learnable query embeddings** — a fixed set of trainable vectors (typically 32 vectors, each of dimension $d_{model}$) that are randomly initialised at the start of training.

Think of them as 32 empty buckets. Before training, they hold no information. As training progresses, each bucket learns to specialise in extracting a specific type of visual information from the frozen ViT's output. After training, one bucket might specialise in "what colour is the dominant object?", another in "is there a living creature?", another in "what is the background setting?", and so on. The model discovers this specialisation entirely from data — no human assigns these roles.

Mechanically, the query embeddings attend to the frozen ViT's output features through **cross-attention**. Cross-attention lets each query vector ask the ViT's representations "give me the information that matches my current state." The ViT's representations act as keys and values; the query embeddings act as queries in the attention formula. This is exactly the attention mechanism from Chapter 1, just applied in a cross-modal context.

$$\text{CrossAttention}(Q_{learned},\; K_{ViT},\; V_{ViT}) = \text{softmax}\left(\frac{Q_{learned}\, K_{ViT}^T}{\sqrt{d_k}}\right) V_{ViT}$$

| Symbol | Meaning |
|--------|---------|
| $Q_{learned}$ | The 32 learnable query embeddings, shape $(32, d_{model})$ |
| $K_{ViT}, V_{ViT}$ | Keys and values derived from the frozen ViT's output features |
| $\sqrt{d_k}$ | Scaling factor to prevent attention score saturation |
| Output | 32 updated query vectors, each carrying compressed visual information |

*This says:* Each learnable query vector computes attention weights over all ViT patch features, then takes a weighted sum of those features as its output. The query that "looks for colour" will naturally assign high attention weights to the patch features that carry colour information, and low weights to everything else.

### 6d. Dry-Run: Q-Former Cross-Attention with Tiny Numbers

Let's walk through the Q-Former's cross-attention mechanism with a minimal example: 2 learnable query vectors, 3 ViT patch representations, and 2-dimensional embeddings.

```
Setup (all vectors 2-dimensional, W_Q = W_K = W_V = I for simplicity):

  Learnable queries:
    Q_learn = [[1.0, 0.0],    ← query 1: initialized to "look in dim-0 direction"
               [0.0, 1.0]]   ← query 2: initialized to "look in dim-1 direction"

  Frozen ViT output (3 patch representations):
    ViT_features = [[0.8, 0.6],   ← patch 1 (imagine: "redness" info lives in dim-0)
                    [0.3, 0.9],   ← patch 2 (imagine: "shape" info lives in dim-1)
                    [0.5, 0.5]]   ← patch 3 (imagine: "background" info, balanced)

  d_k = 2  → sqrt(d_k) = 1.414

Step 1: Compute K and V from ViT features (identity projection)
  K = ViT_features = [[0.8, 0.6], [0.3, 0.9], [0.5, 0.5]]
  V = ViT_features = [[0.8, 0.6], [0.3, 0.9], [0.5, 0.5]]

Step 2: Compute raw attention scores for query 1: Q_learn[0] @ K^T
  Q_learn[0] = [1.0, 0.0]

  score_patch1 = 1.0×0.8 + 0.0×0.6 = 0.8
  score_patch2 = 1.0×0.3 + 0.0×0.9 = 0.3
  score_patch3 = 1.0×0.5 + 0.0×0.5 = 0.5

  Raw scores for query 1: [0.8, 0.3, 0.5]

Step 3: Scale by 1/sqrt(d_k)
  Scaled scores = [0.8/1.414, 0.3/1.414, 0.5/1.414]
                = [0.566,     0.212,     0.354]

Step 4: Softmax to get attention weights
  e^0.566 = 1.761,  e^0.212 = 1.236,  e^0.354 = 1.425
  sum = 1.761 + 1.236 + 1.425 = 4.422

  weights_q1 = [1.761/4.422, 1.236/4.422, 1.425/4.422]
             = [0.398,        0.279,        0.323]
             ← query 1 attends most to patch 1 (the "redness" patch)

Step 5: Compute output for query 1: weights @ V
  output_q1 = 0.398 × [0.8, 0.6]
            + 0.279 × [0.3, 0.9]
            + 0.323 × [0.5, 0.5]

            = [0.318, 0.239]
            + [0.084, 0.251]
            + [0.162, 0.162]

            = [0.564, 0.652]

Now repeat for query 2: Q_learn[1] = [0.0, 1.0]

  score_patch1 = 0.0×0.8 + 1.0×0.6 = 0.6
  score_patch2 = 0.0×0.3 + 1.0×0.9 = 0.9
  score_patch3 = 0.0×0.5 + 1.0×0.5 = 0.5

  Scaled: [0.424, 0.636, 0.354]

  e^0.424 = 1.528,  e^0.636 = 1.889,  e^0.354 = 1.425
  sum = 4.842

  weights_q2 = [0.316, 0.390, 0.294]
               ← query 2 attends most to patch 2 (the "shape" patch)

  output_q2 = 0.316×[0.8,0.6] + 0.390×[0.3,0.9] + 0.294×[0.5,0.5]
            = [0.253, 0.190]
            + [0.117, 0.351]
            + [0.147, 0.147]
            = [0.517, 0.688]

Final Q-Former output (2 updated query vectors):
  output = [[0.564, 0.652],   ← query 1: rich in "redness" info (high dim-0 weight)
            [0.517, 0.688]]   ← query 2: rich in "shape" info   (high dim-1 weight)

Key interpretation:
  → Query 1 (initialized to look in dim-0) naturally attended more to patch 1
    (which has the highest dim-0 value: 0.8) — not because we designed it,
    but because the attention mechanism routes information by similarity.
  → Query 2 (initialized to look in dim-1) naturally attended more to patch 2
    (which has the highest dim-1 value: 0.9).
  → After training, these initial directions get refined — each query learns
    to extract a specific, semantically meaningful type of visual information.
  → The 2 output vectors (or 32 in the real model) are the "distilled visual
    summary" that gets passed downstream to the LLM.
```

*Why this matters:* The cross-attention dry-run shows that the Q-Former is not a mysterious black box — it is the same attention mechanism from Chapter 1, applied between the learnable queries (as Q) and the ViT's patch features (as K and V). The "magic" is that after training, the 32 query vectors have learned which aspects of the image are most useful for driving language generation, entirely from supervision signal coming through the three training tasks.

### 6e. Stage 1: Representation Learning — Three Joint Tasks

Q-Former training happens in two stages. In Stage 1, the Q-Former is trained to represent visual and linguistic information simultaneously. To do this, it is optimised on three tasks at the same time, using image-caption pairs as training data.

```
Stage 1: Vision-and-Language Representation Learning

Input: (image, caption) pairs
       e.g. (🐱 photo, "A pixelated image of a cute cat")

                    frozen ViT  ──► vision features
                                        │ (cross-attention)
  Learnable Queries ──► [Image Transformer] ─┬─► Task 1: Image-Text Contrastive
                                              │
  Caption tokens ───► [Text Transformer]  ───┼─► Task 2: Image-Text Matching
                                              │
                                              └─► Task 3: Image-Grounded Text Generation

  All three tasks are optimised simultaneously via a combined loss
```

**Task 1 — Image-Text Contrastive Learning** works exactly like CLIP. The output of the learnable queries (the "image side" representation) is compared to the caption embedding (the "text side"). Matched pairs are pulled together; unmatched pairs are pushed apart. This teaches the Q-Former the coarse semantic alignment between images and text — what things go together.

**Task 2 — Image-Text Matching** is a binary classification task. Given the paired image and text representations, a small classifier predicts: is this a genuine matched pair (1) or a random pairing (0)? This is a finer-grained task than contrastive learning. Contrastive learning only sees one positive pair per row of the similarity matrix; matching sees every individual pair and labels it. This forces the model to understand subtle mismatches that contrastive loss might miss.

**Task 3 — Image-Grounded Text Generation** trains the Q-Former to actually *generate* the caption from the image. The caption is fed to the Text Transformer, and the model must produce the caption tokens autoregressively, conditioned on the visual information extracted by the learnable queries. This is the hardest task — it demands that the query embeddings capture enough complete visual information to drive coherent text generation.

Why are all three tasks needed? They address different failure modes. Contrastive learning alone gives coarse semantic alignment but might be satisfied by very rough visual features. Matching alone is too local — it only knows positive vs. negative, not richer nuance. Generation alone might memorise captions without building genuinely visual representations. Together, they create a Q-Former that is globally aligned, locally discriminative, and semantically complete.

### 6f. Stage 2: Vision-to-Language — Soft Visual Prompts

After Stage 1, the 32 learnable query embeddings have learned to compress rich visual information from the frozen ViT. Stage 2 connects this visual representation to the frozen LLM.

The procedure is simple: the 32 updated query embeddings are passed through a **fully connected linear projection layer** that maps them from Q-Former's $d_{model}$ dimension to the LLM's embedding dimension. This is necessary because Q-Former and the LLM typically have different hidden sizes.

The projected embeddings are then **prepended to the LLM's input token sequence** as if they were ordinary text tokens. From the LLM's perspective, it receives a sequence that starts with 32 "token" embeddings (which actually encode the image) followed by the text tokens of the actual prompt.

These are called **soft visual prompts** because:
- *Soft*: they are continuous floating-point vectors, not discrete vocabulary tokens. They cannot be decoded back into words. The LLM never "sees" the image — it sees continuous vectors that carry visual information in the LLM's preferred representation.
- *Visual prompts*: they condition the LLM's generation, just as text prompts do in standard prompting.

The LLM is frozen and never updated. It simply responds to the combined input of soft visual prompts + text tokens, producing text output. The genius of this approach is that the LLM requires no modification — it was already designed to process sequences of embedding vectors, and the soft visual prompts look like just more vectors at the front of the sequence.

### 6g. Full BLIP-2 Pipeline Diagram

```
                                BLIP-2 Full Pipeline

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                          STAGE 1 (Training)                            │
  │                                                                         │
  │   Input Image                                                           │
  │       │                                                                 │
  │       ▼                                                                 │
  │  [❄ Frozen ViT]  ──────────────────────── vision features              │
  │                                                 │ (cross-attention)     │
  │  Learnable Queries ──► [🔥 Q-Former] ◄──────────┘                      │
  │  [Q1][Q2]...[Q32]         │   │                                         │
  │                           │   └── [Text Transformer] ◄── Caption Text  │
  │                           │                                             │
  │               ┌───────────┼───────────┐                                 │
  │               ▼           ▼           ▼                                 │
  │         Contrastive    Matching   Generation                            │
  │           Loss          Loss        Loss                                │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                          STAGE 2 (Training)                            │
  │                                                                         │
  │   Input Image                                                           │
  │       │                                                                 │
  │       ▼                                                                 │
  │  [❄ Frozen ViT] → vision features                                       │
  │                          │                                              │
  │  Learnable Queries → [🔥 Q-Former]                                      │
  │                          │                                              │
  │                          ▼ 32 query output vectors                      │
  │                  [🔥 Linear Projection]  ← adjusts dimensions           │
  │                          │                                              │
  │                          ▼ 32 projected embeddings                      │
  │  ┌──────────────────────────────────────────────────┐                   │
  │  │ [sv1][sv2]...[sv32] [Q:][text][tokens]           │ → [❄ Frozen LLM] │
  │  │  soft visual prompts (image info)   text prompt  │                  │
  │  └──────────────────────────────────────────────────┘                   │
  │                          │                                              │
  │                          ▼                                              │
  │                  Generated Text Output                                  │
  └─────────────────────────────────────────────────────────────────────────┘
```

### 6h. LLaVA and Idefics 2 — The Same Idea, Different Variants

The Q-Former/bridge approach that BLIP-2 pioneered became a template for an entire family of visual LLMs.

**LLaVA** (Large Language and Vision Assistant) uses a simpler bridge — a single linear projection layer instead of the full Q-Former — connecting a frozen CLIP image encoder to a frozen LLM (LLaMA). It compensates for the simpler bridge by using instruction-following data for training: instead of image-caption pairs, it trains on multi-turn conversations about images generated by GPT-4. LLaVA is widely used because its architecture is simpler and its conversational capabilities are strong.

**Idefics 2** is an efficient visual LLM based on Mistral 7B. It connects a pretrained CLIP-like visual encoder to Mistral through a projection layer, and adds multimodal instruction tuning. It achieves near-LLaVA quality at lower computational cost.

The key takeaway is architectural: all of these models share the pattern of *frozen visual encoder → projection bridge → frozen LLM*. The visual encoder and LLM bring their respective expertise; the bridge is the only thing that needs to learn.

---

## 7. BLIP-2 in Practice: Preprocessing Multimodal Inputs

### 7a. The Processor — Like a Tokenizer for Images + Text

When working with text-only models, you use a tokenizer to convert raw text into the integer token IDs the model expects. BLIP-2 has an equivalent abstraction called a **processor** — a single object that handles both image preprocessing and text tokenization.

```python
from transformers import AutoProcessor, Blip2ForConditionalGeneration
import torch

# Load processor (handles both image and text)
blip_processor = AutoProcessor.from_pretrained("Salesforce/blip2-opt-2.7b")

# Load the main BLIP-2 model (ViT + Q-Former + OPT-2.7B LLM)
model = Blip2ForConditionalGeneration.from_pretrained(
    "Salesforce/blip2-opt-2.7b",
    torch_dtype=torch.float16   # half precision to fit in GPU memory
)

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

# Inspect the components
model.vision_model    # the frozen ViT
model.language_model  # the frozen OPT-2.7B LLM
```

The processor can be thought of as having two internal components: an image preprocessor (handles resizing, normalisation, channel ordering) and a text tokenizer (GPT2-based, handles subword tokenization).

### 7b. Image Preprocessing: Any Size → 224×224

The frozen ViT inside BLIP-2 was trained on 224×224 pixel images. No matter what size image you provide, the processor will resize it to 224×224. This is important to understand because it has a practical consequence: **images with unusual aspect ratios will be distorted**.

The 224×224 constraint is not arbitrary — it is the exact resolution ViT was pre-trained on. Changing it would require re-training the ViT (which is frozen). The number 224 comes from historical convention: early CNN papers used 224×224 because it divided cleanly by the typical stride and pooling sizes, and ViT adopted the same resolution for compatibility. For the patch size of 16×16, a 224×224 image produces 14×14 = 196 patches — a manageable sequence length.

```python
# Load a very wide image (520×492 pixels)
image = Image.open(urlopen(car_path)).convert("RGB")

# Preprocess
inputs = blip_processor(image, return_tensors="pt").to(device, torch.float16)
inputs["pixel_values"].shape
# → torch.Size([1, 3, 224, 224])
# batch=1, RGB channels=3, height=224, width=224
```

The 520×492 original becomes a 224×224 square. A wide landscape photo will have its sides compressed; a tall portrait will have its top and bottom compressed. This is a practical gotcha — if you feed BLIP-2 highly non-square images (panoramas, tall screenshots), the distortion may confuse the model.

### 7c. Text Preprocessing: GPT2Tokenizer Quirks

BLIP-2's OPT-2.7B LLM uses a **GPT2Tokenizer** with a vocabulary of 50,265 tokens. The tokenizer behaves slightly differently from BERT-style tokenizers in one notable way: spaces at the beginning of words are represented by the Ĝ character.

```python
# Access the underlying tokenizer
blip_processor.tokenizer
# GPT2TokenizerFast(vocab_size=50265, ...)

# Tokenize a sentence
text = "Her vocalization was remarkably melodic"
token_ids = blip_processor(image, text=text, return_tensors="pt")["input_ids"][0]
tokens = blip_processor.tokenizer.convert_ids_to_tokens(token_ids)
# → ['</s>', 'Her', 'Ĝvocal', 'ization', 'Ĝwas', 'Ĝremarkably', 'Ĝmel', 'odic']

# Replace Ĝ with underscore for readability
tokens = [t.replace("Ĝ", "_") for t in tokens]
# → ['</s>', 'Her', '_vocal', 'ization', '_was', '_remarkably', '_mel', 'odic']
```

The Ĝ symbol appears because GPT2's tokenizer internally moves characters in certain code points up by 256 to make them printable. The space character (Unicode code point 32) becomes code point 288, which renders as Ĝ. The underscore at the start of `_was` and `_remarkably` tells you these tokens begin a new word (they were preceded by a space in the original text).

Also note that in CLIP, the `[CLS]` token is used to represent the entire image as a single embedding. In BLIP-2's text path, the `</s>` token that appears at the start serves as the start-of-sequence marker for the GPT2-family tokenizer.

---

## 8. Use Case 1 — Image Captioning

### 8a. How It Works End-to-End

Image captioning is the most direct application of BLIP-2: give the model an image, get back a text description. The pipeline follows directly from the BLIP-2 architecture:

```
Input Image
    │
    ▼  blip_processor (resize to 224×224, normalise)
pixel_values  shape: [1, 3, 224, 224]
    │
    ▼  frozen ViT (extract visual features)
vision_features  (intermediate representation)
    │
    ▼  Q-Former (32 learnable queries cross-attend to vision features)
query_outputs  shape: [1, 32, d_model]
    │
    ▼  Linear Projection
soft_visual_prompts  shape: [1, 32, llm_d_model]
    │
    ▼  Frozen OPT-2.7B LLM (autoregressively generates text)
generated_token_ids
    │
    ▼  blip_processor.batch_decode(skip_special_tokens=True)
"an orange supercar driving on the road at sunset"
```

The model has no text prompt — it receives only the image. The LLM, conditioned purely on the 32 soft visual prompts, generates the most likely caption.

### 8b. Code Walkthrough

```python
# Load the image (a supercar)
image = Image.open(urlopen(car_path)).convert("RGB")

# Preprocess image into pixel values the model expects
inputs = blip_processor(image, return_tensors="pt").to(device, torch.float16)
# inputs["pixel_values"].shape → [1, 3, 224, 224]

# Run the full pipeline: ViT → Q-Former → LLM → token IDs
generated_ids = model.generate(**inputs, max_new_tokens=20)
# generated_ids → tensor of integer token IDs

# Decode token IDs back to text
generated_text = blip_processor.batch_decode(
    generated_ids,
    skip_special_tokens=True   # removes </s>, <pad> tokens
)
generated_text = generated_text[0].strip()
print(generated_text)
# → "an orange supercar driving on the road at sunset"
```

The `model.generate()` call handles the autoregressive decoding — at each step, the LLM predicts the next token conditioned on all previous tokens and the soft visual prompts. `max_new_tokens=20` limits the caption length.

**Fun example — the Rorschach test:**

```python
# Load a Rorschach inkblot image
image = Image.open(urlopen(rorschach_url)).convert("RGB")
inputs = blip_processor(image, return_tensors="pt").to(device, torch.float16)
generated_ids = model.generate(**inputs, max_new_tokens=20)
generated_text = blip_processor.batch_decode(generated_ids, skip_special_tokens=True)
# → "a black and white ink drawing of a bat"
```

BLIP-2 saw the inkblot and described it as a bat — which is, arguably, a reasonable interpretation!

### 8c. Limitations

BLIP-2's training data is dominated by publicly available internet images with natural captions. This creates real limitations in the types of images it can describe well.

| Image Type | BLIP-2 Performance | Why |
|------------|-------------------|-----|
| Natural photographs (common objects) | Good | Well-represented in training data |
| AI-generated images | Moderate | Different visual statistics than photos |
| Medical scans (X-ray, MRI) | Poor | Rare in public internet data |
| Satellite or aerial imagery | Poor | Specialised visual domain |
| Technical diagrams / charts | Poor | Text-heavy visuals, different rendering |
| Cartoon / anime characters | Variable | Style mismatch with photo training data |
| Very small details (sub-10px) | Poor | Lost in 224×224 downsampling |
| Non-square panoramas | Variable | Aspect ratio distortion during preprocessing |

These limitations are not bugs — they are the natural consequence of training on public data. Addressing them requires fine-tuning BLIP-2 on domain-specific datasets. The model's authors note that it can also produce hallucinated captions for unusual images — confidently describing something that isn't there.

---

## 9. Use Case 2 — Multimodal Chat-Based Prompting

### 9a. Visual Question Answering

Image captioning generates an unprompted description. **Visual Question Answering (VQA)** goes further: you provide both an image and a question, and the model answers the question using information from the image. This requires the model to simultaneously understand the visual content and the linguistic question, then synthesise a relevant answer.

The key change in the code is adding a text prompt:

```python
image = Image.open(urlopen(car_path)).convert("RGB")

# Now provide a question along with the image
prompt = "Question: Write down what you see in this picture. Answer:"

# Process both image AND text together
inputs = blip_processor(
    image,
    text=prompt,
    return_tensors="pt"
).to(device, torch.float16)

# Generate answer
generated_ids = model.generate(**inputs, max_new_tokens=30)
generated_text = blip_processor.batch_decode(generated_ids, skip_special_tokens=True)
generated_text = generated_text[0].strip()
# → "A sports car driving on the road at sunset"
```

The prompt format `"Question: {question} Answer:"` is the expected template for BLIP-2's OPT-based model. The text prompt is tokenised and appended *after* the 32 soft visual prompts in the LLM's input sequence. The LLM sees: `[visual_prompt_1...32][Question:][...text...][Answer:]` and generates the answer continuation.

### 9b. Chat-Like Memory Prompting

BLIP-2 can maintain a conversational context about an image by including the full conversation history in each subsequent prompt. This is the same technique as few-shot prompting in text-only models — you explicitly provide prior exchanges in the prompt string.

```python
# First turn: initial question
prompt = "Question: Write down what you see in this picture. Answer:"
# → BLIP-2: "A sports car driving on the road at sunset"

# Second turn: include first exchange in the prompt, add new question
prompt = (
    "Question: Write down what you see in this picture. "
    "Answer: A sports car driving on the road at sunset. "
    "Question: What would it cost to drive such a car? "
    "Answer:"
)
# → BLIP-2: "$1,000,000"

# Third turn: include first two exchanges
prompt = (
    "Question: Write down what you see in this picture. "
    "Answer: A sports car driving on the road at sunset. "
    "Question: What would it cost to drive such a car? "
    "Answer: $1,000,000. "
    "Question: Why that much money? "
    "Answer:"
)
# → BLIP-2: "Because it's a sports car."
```

The image never changes — the same 32 soft visual prompts are prepended in every call. The LLM is simply given a longer text context to condition on. The diagram below shows why this works: the image is a constant anchor in the context window.

```
Multi-Turn BLIP-2 Conversation — What the LLM Sees Each Turn

Turn 1:
  [sv1..sv32] [Question: What do you see?] [Answer:]
        │
        └── soft visual prompts (image, constant across all turns)

Turn 2:
  [sv1..sv32] [Question: What do you see?] [Answer: A sports car...]
              [Question: What does it cost?] [Answer:]
        │
        └── same soft visual prompts + conversation history appended

Turn 3:
  [sv1..sv32] [Question: What do you see?] [Answer: A sports car...]
              [Question: What does it cost?] [Answer: $1,000,000.]
              [Question: Why that much?] [Answer:]
        │
        └── same soft visual prompts + growing conversation history

The model sees the image (via sv1..sv32) AND the full conversation at every turn.
"Memory" is implemented as context window accumulation — no hidden state is updated.
```

### 9c. Building an Interactive Chatbot with ipywidgets

The book implements a full interactive visual chatbot in a Jupyter notebook using `ipywidgets`. The pattern maintains a `memory` list of (question, answer) tuples that is updated after each exchange.

```python
from IPython.display import HTML, display
import ipywidgets as widgets

memory = []  # stores (question, answer) pairs

def text_eventhandler(*args):
    question = args[0]["new"]
    if not question:
        return
    args[0]["owner"].value = ""  # clear input box after reading

    # Build prompt from conversation history + new question
    if not memory:
        prompt = " Question: " + question + " Answer:"
    else:
        template = "Question: {} Answer: {}."
        prior = " ".join([template.format(q, a) for q, a in memory])
        prompt = prior + " Question: " + question + " Answer:"

    # Generate response (image is fixed — same soft visual prompts every time)
    inputs = blip_processor(image, text=prompt, return_tensors="pt")
    inputs = inputs.to(device, torch.float16)
    generated_ids = model.generate(**inputs, max_new_tokens=100)
    generated_text = blip_processor.batch_decode(
        generated_ids, skip_special_tokens=True
    )
    # Take only the first answer — split on "Question" to avoid echoing history
    answer = generated_text[0].strip().split("Question")[0]

    memory.append((question, answer))

    output.append_display_data(HTML("<b>USER:</b> " + question))
    output.append_display_data(HTML("<b>BLIP-2:</b> " + answer))
    output.append_display_data(HTML("<br>"))

# Widget layout — text input at bottom, conversation history above
in_text = widgets.Text()
in_text.continuous_update = False
in_text.observe(text_eventhandler, "value")
output = widgets.Output()
display(widgets.VBox(
    children=[output, in_text],
    layout=widgets.Layout(display="inline-flex", flex_flow="column-reverse")
))
```

A sample conversation this produces:

```
USER:   Write down what you see in this picture.
BLIP-2: A sports car driving on the road at sunset

USER:   What would it cost me to drive that car?
BLIP-2: $1,000,000

USER:   Why that much money?
BLIP-2: Because it's a sports car.

USER:   Why are sports cars expensive?
BLIP-2: Because they're fast.
```

The key insight: the image is processed once into 32 soft visual prompts, and those prompts are reused in every call. The model effectively "remembers" the image throughout the entire conversation via these fixed visual embeddings. This is what makes the chatbot coherent — every answer is conditioned on the same visual context.

---

## 10. Key Takeaways

The Vision Transformer (ViT) solves the image tokenization problem by cutting images into fixed-size patches, linearly projecting each patch into an embedding vector, and feeding the sequence to a standard Transformer encoder. From that point forward, the architecture is identical to text processing — images become sequences of patch embeddings, treated by the model as if they were word tokens. This elegant unification is what makes ViT the foundation of all modern vision-language systems.

CLIP trains two encoders — a ViT for images and a Transformer for text — to produce embeddings in the same 512-dimensional vector space. Contrastive learning pulls matched image-caption pairs together and pushes unmatched pairs apart, across 400 million examples. The result is a universal cross-modal embedding space enabling zero-shot classification, cross-modal search, and the conditioning of image generation models like Stable Diffusion.

BLIP-2 solves the problem of making a text generation LLM see images without retraining either the vision model or the LLM. The Q-Former — a small, trainable bridge — extracts visual information from a frozen ViT through 32 learnable query embeddings, compresses it into soft visual prompts via a linear projection, and prepends those prompts to the frozen LLM's input. Only the Q-Former is trained; the ViT and LLM remain frozen throughout.

The Q-Former's Stage 1 training uses three simultaneous objectives — contrastive learning, image-text matching, and image-grounded text generation — because each objective addresses a different failure mode in visual-language alignment. Using all three produces a more complete and robust visual representation than any single objective alone. The cross-attention mechanism inside Q-Former is identical to the attention from Chapter 1: learnable query vectors attend over ViT patch features as keys and values, extracting the most relevant visual information for the task at hand.

The architectural pattern of *frozen visual encoder → trainable projection bridge → frozen LLM* became the template for an entire family of visual LLMs, including LLaVA, Idefics 2, and Flamingo. The chapter's practitioner lesson is that you rarely need to train from scratch — combining a frozen CLIP model with a frozen LLM through a small bridge gives you a powerful multimodal system at a fraction of the compute cost.

### When to Use What

Choosing the right model for a multimodal task depends on whether you need to *find* things or *understand and explain* them. CLIP-family models excel at retrieval and classification because their embeddings live in a shared space ideal for similarity search. BLIP-2 and its variants excel at generation tasks because they connect visual understanding to a full language model capable of nuanced text output.

| Model | Best For | Not Ideal For | Compute Cost | Key Library |
|-------|----------|--------------|--------------|-------------|
| `openai/clip-vit-base-patch32` | Cross-modal search, zero-shot classification | Generating text answers | Low (embedding only) | `transformers` |
| `clip-ViT-B-32` (sentence-transformers) | Same as above, simpler API | — | Low | `sentence-transformers` |
| `Salesforce/blip2-opt-2.7b` | Visual QA, image captioning, multimodal chat | Real-time / edge deployment | High (7B LLM) | `transformers` |
| LLaVA variants | Instruction-following conversations about images | Pure retrieval tasks | High | `llava` |
| ViT (standalone, `google/vit-base-patch16-224`) | Image feature extraction for custom pipelines | Direct text comparison | Medium | `transformers` |

*Plain-English rule:* If you need to **find** something — retrieve images from a database, classify without labels, compare an image to a set of descriptions — use CLIP. If you need to **understand and explain** something — answer questions about an image, caption a photo, have a conversation about visual content — use BLIP-2 or LLaVA.

### Connection Forward

Chapter 10 goes deeper into contrastive learning as a training paradigm, applied now to text-only embeddings. The same InfoNCE loss that CLIP uses to align images and text appears again in SBERT-style training. The same batch-level negative mining — using all other examples in the batch as negatives — becomes the Multiple Negatives Ranking Loss. Understanding CLIP's contrastive training in this chapter gives you the perfect foundation for understanding how high-quality sentence embedding models are built in Chapter 10.
