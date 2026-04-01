# GPT-2 Pipeline: Master Task List

> Reproduce the book's complete pipeline from scratch — architecture → pretraining →
> classification fine-tuning → instruction fine-tuning on GPT-2 medium (355M).
> Each task has: what to build, the exact function signature, what it returns, and
> which note to refer to for theory.

---

## How to use this list

- Work top to bottom. Each task depends on everything above it.
- **Write the function first, then test it** before moving on.
- The "Theory note" column tells you exactly which section of your notes to re-read
  if you get stuck — don't reach for GitHub until you've tried from your notes.
- `[ ]` = not started · `[~]` = in progress · `[x]` = done

---

## PHASE 1 — Data Pipeline (Ch. 2)

### 1.1 Tokenizer setup

```
[ ] Task: Load the GPT-2 BPE tokenizer via tiktoken

    import tiktoken
    tokenizer = tiktoken.get_encoding("gpt2")

    # Verify:
    ids  = tokenizer.encode("Hello, world!")   # → list[int]
    text = tokenizer.decode(ids)               # → "Hello, world!"
    # vocab size must be 50257

    Theory note: ch02 notes — "Tokenising text / BPE"
```

---

### 1.2 Token-ID utility functions

```
[ ] Task: Two tiny helpers used throughout all future chapters

    def text_to_token_ids(text: str, tokenizer) -> torch.Tensor:
        """
        Encode text → 1-D token-id tensor with batch dim.
        Returns: Tensor shape (1, seq_len)  — unsqueeze(0) for batch dim
        """

    def token_ids_to_text(token_ids: torch.Tensor, tokenizer) -> str:
        """
        Decode token-id tensor → string.
        Accepts shape (1, seq_len) or (seq_len,).
        Returns: decoded string
        """

    Theory note: ch05 notes — "5.1 Evaluating generative text models"
```

---

### 1.3 Dataset class

```
[ ] Task: Sliding-window dataset for pretraining

    class GPTDatasetV1(Dataset):
        def __init__(
            self,
            txt: str,           # raw text corpus
            tokenizer,          # tiktoken encoder
            max_length: int,    # context window size (e.g. 256 for training, 1024 for GPT-2)
            stride: int         # how many tokens to advance each window
        ):
            ...
            # self.input_ids  : list of Tensors, each shape (max_length,)
            # self.target_ids : list of Tensors, each shape (max_length,)
            # target = input shifted right by 1

        def __len__(self) -> int: ...
        def __getitem__(self, idx) -> tuple[Tensor, Tensor]: ...

    Theory note: ch02 notes — "Sliding window / GPTDatasetV1"
```

---

### 1.4 DataLoader factory

```
[ ] Task: Wrap dataset in a PyTorch DataLoader

    def create_dataloader_v1(
        txt: str,
        batch_size: int   = 4,
        max_length: int   = 256,
        stride: int       = 128,
        shuffle: bool     = True,
        drop_last: bool   = True,
        num_workers: int  = 0
    ) -> DataLoader:
        """
        Returns a DataLoader that yields (input_ids, target_ids) batches.
        Each batch shape: (batch_size, max_length)
        """

    # Quick sanity check after writing:
    # batch = next(iter(loader))
    # assert batch[0].shape == (batch_size, max_length)

    Theory note: ch02 notes — "create_dataloader_v1"
```

---

## PHASE 2 — Model Architecture (Ch. 3 & 4)

### 2.1 Causal self-attention (single head)

```
[ ] Task: Build CausalAttention — one attention head with causal mask

    class CausalAttention(nn.Module):
        def __init__(
            self,
            d_in: int,          # input embedding dim
            d_out: int,         # output dim (= head dim)
            context_length: int,# max seq len — needed to register causal mask
            dropout: float,
            qkv_bias: bool = False
        ): ...

        def forward(self, x: Tensor) -> Tensor:
            # x shape: (batch, seq_len, d_in)
            # returns: (batch, seq_len, d_out)

    Theory note: ch03 notes — "3.4 / 3.5 Causal self-attention"
```

---

### 2.2 Multi-head attention

```
[ ] Task: Efficient MultiHeadAttention (split-head, NOT stacked CausalAttention)

    class MultiHeadAttention(nn.Module):
        def __init__(
            self,
            d_in: int,
            d_out: int,          # total output dim = num_heads * head_dim
            context_length: int,
            dropout: float,
            num_heads: int,
            qkv_bias: bool = False
        ): ...

        def forward(self, x: Tensor) -> Tensor:
            # x:      (batch, seq_len, d_in)
            # returns:(batch, seq_len, d_out)
            # Key shapes to verify:
            #   W_query, W_key, W_value: Linear(d_in, d_out)
            #   head_dim = d_out // num_heads
            #   after split: (batch, num_heads, seq_len, head_dim)
            #   out_proj: Linear(d_out, d_out)

    Theory note: ch03 notes — "3.6 Multi-head attention"
```

---

### 2.3 Layer normalization

```
[ ] Task: Pre-norm LayerNorm (NOT PyTorch's built-in — implement manually)

    class LayerNorm(nn.Module):
        def __init__(self, emb_dim: int):
            # learnable: self.scale (ones), self.shift (zeros)
            # self.eps = 1e-5

        def forward(self, x: Tensor) -> Tensor:
            # x: (..., emb_dim)
            # compute mean and var over last dim
            # returns normalised + scaled + shifted tensor, same shape

    Theory note: ch04 notes — "4.2 Layer normalisation"
```

---

### 2.4 GELU activation

```
[ ] Task: GELU approximation (tanh version used by GPT-2)

    class GELU(nn.Module):
        def forward(self, x: Tensor) -> Tensor:
            # return 0.5 * x * (1 + tanh(sqrt(2/pi) * (x + 0.044715 * x^3)))

    Theory note: ch04 notes — "4.2 GELU activation"
```

---

### 2.5 Feed-forward block

```
[ ] Task: Position-wise feed-forward network

    class FeedForward(nn.Module):
        def __init__(self, cfg: dict):
            # cfg["emb_dim"] → hidden dim
            # Linear(emb_dim, 4*emb_dim) → GELU → Linear(4*emb_dim, emb_dim)

        def forward(self, x: Tensor) -> Tensor:
            # x: (batch, seq_len, emb_dim)
            # returns: same shape

    Theory note: ch04 notes — "4.3 Feed-forward network with GELU"
```

---

### 2.6 Transformer block

```
[ ] Task: Single transformer block (Pre-LN, two residual connections)

    class TransformerBlock(nn.Module):
        def __init__(self, cfg: dict):
            # self.att  = MultiHeadAttention(...)
            # self.ff   = FeedForward(cfg)
            # self.norm1 = LayerNorm(cfg["emb_dim"])
            # self.norm2 = LayerNorm(cfg["emb_dim"])
            # self.drop_shortcut = nn.Dropout(cfg["drop_rate"])

        def forward(self, x: Tensor) -> Tensor:
            # Sub-block 1: shortcut → norm1 → att → dropout → add
            # Sub-block 2: shortcut → norm2 → ff  → dropout → add
            # returns: (batch, seq_len, emb_dim) — SAME shape as input

    Theory note: ch04 notes — "4.5 TransformerBlock assembly"
```

---

### 2.7 Full GPT model

```
[ ] Task: Full GPTModel — the complete architecture

    GPT_CONFIG_124M = {
        "vocab_size":     50257,
        "context_length": 256,    # use 256 for training; switch to 1024 when loading weights
        "emb_dim":        768,
        "n_heads":        12,
        "n_layers":       12,
        "drop_rate":      0.1,
        "qkv_bias":       False
    }

    class GPTModel(nn.Module):
        def __init__(self, cfg: dict):
            # self.tok_emb   = nn.Embedding(vocab_size, emb_dim)
            # self.pos_emb   = nn.Embedding(context_length, emb_dim)
            # self.drop_emb  = nn.Dropout(drop_rate)
            # self.trf_blocks= nn.Sequential(*[TransformerBlock(cfg) for _ in range(n_layers)])
            # self.final_norm= LayerNorm(emb_dim)
            # self.out_head  = nn.Linear(emb_dim, vocab_size, bias=False)

        def forward(self, in_idx: Tensor) -> Tensor:
            # in_idx: (batch, seq_len)
            # 1. tok_emb(in_idx) + pos_emb(arange(seq_len))
            # 2. drop_emb
            # 3. trf_blocks
            # 4. final_norm
            # 5. out_head
            # returns logits: (batch, seq_len, vocab_size)

    # Verify:
    # model = GPTModel(GPT_CONFIG_124M)
    # x = torch.randint(0, 50257, (2, 4))
    # out = model(x)
    # assert out.shape == (2, 4, 50257)
    # total params ≈ 163M (124M for small)

    Theory note: ch04 notes — "4.6 The full GPTModel"
```

---

### 2.8 Simple text generation

```
[ ] Task: Greedy / argmax generation (no temperature yet)

    def generate_text_simple(
        model: GPTModel,
        idx: Tensor,             # (batch, seq_len) seed token ids
        max_new_tokens: int,
        context_size: int        # model's context_length
    ) -> Tensor:
        """
        Auto-regressively generate max_new_tokens new tokens.
        At each step: crop to context_size, forward pass,
        take last token logit, argmax, append.
        Returns: (batch, seq_len + max_new_tokens)
        """

    Theory note: ch04 notes — "4.7 generate_text_simple"
```

---

## PHASE 3 — Pretraining (Ch. 5)

### 3.1 Loss on a single batch

```
[ ] Task: Cross-entropy loss for one batch

    def calc_loss_batch(
        input_batch: Tensor,    # (batch, seq_len)
        target_batch: Tensor,   # (batch, seq_len)
        model: GPTModel,
        device: torch.device
    ) -> Tensor:
        """
        Move tensors to device.
        Forward pass → logits (batch, seq_len, vocab_size).
        Flatten to (batch*seq_len, vocab_size) and (batch*seq_len,).
        Return: F.cross_entropy(logits_flat, targets_flat)  — scalar tensor
        """

    Theory note: ch05 notes — "5.1 calc_loss_batch"
```

---

### 3.2 Loss over a DataLoader

```
[ ] Task: Average loss across multiple batches

    def calc_loss_loader(
        data_loader: DataLoader,
        model: GPTModel,
        device: torch.device,
        num_batches: int = None   # None = use all batches
    ) -> float:
        """
        Loop over data_loader (up to num_batches).
        Accumulate calc_loss_batch results.
        Return: mean loss as Python float
        Use torch.no_grad() — this is evaluation only.
        """

    Theory note: ch05 notes — "5.1 calc_loss_loader"
```

---

### 3.3 Model evaluation helper

```
[ ] Task: Evaluate train and val loss in one call

    def evaluate_model(
        model: GPTModel,
        train_loader: DataLoader,
        val_loader: DataLoader,
        device: torch.device,
        eval_iter: int           # number of batches to evaluate on
    ) -> tuple[float, float]:
        """
        Set model.eval(), compute train and val loss via calc_loss_loader.
        Set model.train() before returning.
        Returns: (train_loss, val_loss)
        """

    Theory note: ch05 notes — "5.2 evaluate_model"
```

---

### 3.4 Print a generation sample during training

```
[ ] Task: Generate and decode a sample sentence mid-training

    def generate_and_print_sample(
        model: GPTModel,
        tokenizer,
        device: torch.device,
        start_context: str       # e.g. "Every effort moves you"
    ) -> None:
        """
        model.eval() → encode start_context → generate_text_simple(50 tokens)
        → decode → print → model.train()
        Gives a qualitative check of model quality during training.
        """

    Theory note: ch05 notes — "5.2 generate_and_print_sample"
```

---

### 3.5 Training loop

```
[ ] Task: Full pretraining loop

    def train_model_simple(
        model: GPTModel,
        train_loader: DataLoader,
        val_loader: DataLoader,
        optimizer: torch.optim.Optimizer,
        device: torch.device,
        num_epochs: int,
        eval_freq: int,          # evaluate every N steps
        eval_iter: int,          # num batches for evaluate_model
        start_context: str,      # seed text for generate_and_print_sample
        tokenizer
    ) -> tuple[list, list, list]:
        """
        Outer loop: epochs. Inner loop: batches.
        Each step: zero_grad → calc_loss_batch → backward → step.
        Every eval_freq steps: evaluate_model → log losses.
        End of each epoch: generate_and_print_sample.
        Returns: (train_losses, val_losses, tokens_seen)
        """

    # Recommended hyperparams for first run:
    # optimizer = AdamW(model.parameters(), lr=0.0004, weight_decay=0.1)
    # num_epochs = 10, eval_freq = 5, eval_iter = 5

    Theory note: ch05 notes — "5.2 train_model_simple"
```

---

### 3.6 Advanced generation (temperature + top-k)

```
[ ] Task: Probabilistic generation with sampling controls

    def generate(
        model: GPTModel,
        idx: Tensor,             # (batch, seq_len) seed
        max_new_tokens: int,
        context_size: int,
        temperature: float = 0.0,  # 0 = greedy (argmax)
        top_k: int = None,         # None = no filtering
        eos_id: int = None         # stop early on this token id
    ) -> Tensor:
        """
        Same loop as generate_text_simple, but with:
          1. top-k masking: zero out logits below k-th highest
          2. temperature scaling: logits / temperature → softmax → multinomial
          3. eos early stopping: break if idx_next == eos_id
        """

    Theory note: ch05 notes — "5.3 generate() with temperature and top-k"
```

---

### 3.7 Save and load model weights

```
[ ] Task: Persist training state to disk

    # Save:
    torch.save({
        "model_state_dict":     model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
    }, "model_checkpoint.pth")

    # Load:
    checkpoint = torch.load("model_checkpoint.pth", weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

    Theory note: ch05 notes — "5.4 Saving and loading model weights"
```

---

### 3.8 Load pretrained GPT-2 weights (OpenAI)

```
[ ] Task: Download OpenAI weights and map into GPTModel

    # Step 1 — update config to match real GPT-2:
    NEW_CONFIG = GPT_CONFIG_124M.copy()
    NEW_CONFIG.update({
        "context_length": 1024,  # real GPT-2 context
        "qkv_bias": True,        # OpenAI used QKV bias
    })
    # For medium: also update emb_dim=1024, n_heads=16, n_layers=24

    # Step 2 — download and load:
    from gpt_download import download_and_load_gpt2

    settings, params = download_and_load_gpt2(
        model_size="124M",       # or "355M" for medium
        models_dir="gpt2"
    )
    # settings: dict of architecture hyperparams
    # params:   dict of NumPy weight arrays

    # Step 3 — build model and load weights:
    def load_weights_into_gpt(gpt: GPTModel, params: dict) -> None:
        """
        Manually map params (OpenAI naming) into gpt (book naming).
        Key mappings to implement:
          params["wte"]  → gpt.tok_emb.weight
          params["wpe"]  → gpt.pos_emb.weight
          params["b"]    → gpt.final_norm.shift (bias)
          params["g"]    → gpt.final_norm.scale
          for each block b:
            params["blocks"][b]["attn"]["c_attn"] → split into W_query/W_key/W_value
            params["blocks"][b]["mlp"]["c_fc"]    → FeedForward first linear
            ... (transpose where needed — OpenAI uses conv1D convention)
        Tip: use assign() helper that checks shapes before assigning.
        """

    # Step 4 — verify with generation:
    # model.eval()
    # output = generate(model, text_to_token_ids("Every effort moves", tokenizer),
    #                   max_new_tokens=25, context_size=1024)
    # should produce coherent English

    Theory note: ch05 notes — "5.5 Loading pretrained weights from OpenAI"
```

---

## PHASE 4 — Classification Fine-Tuning (Ch. 6)

> Target: GPT-2 small (124M) for spam classification.

### 4.1 Download and prepare spam dataset

```
[ ] Task: SMS Spam Collection — download, balance, split

    def download_and_unzip_spam_data(
        url: str,
        zip_path: str,
        extracted_path: str,
        data_file_path: Path
    ) -> None:
        """Download zip, extract TSV. Skip if already exists."""

    def create_balanced_dataset(df: pd.DataFrame) -> pd.DataFrame:
        """
        Undersample majority class (ham) to match minority class (spam).
        Returns balanced DataFrame with equal ham/spam counts.
        """

    def random_split(
        df: pd.DataFrame,
        train_frac: float = 0.70,
        val_frac:   float = 0.10
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Returns (train_df, val_df, test_df). test = remaining 20%."""

    Theory note: ch06 notes — "6.2 Preparing the Dataset"
```

---

### 4.2 Spam dataset class

```
[ ] Task: PyTorch Dataset for classification

    class SpamDataset(Dataset):
        def __init__(
            self,
            csv_file: str,
            tokenizer,
            max_length: int = None,    # None = use longest in dataset
            pad_token_id: int = 50256  # <|endoftext|> used as pad
        ):
            # self.data = pd.read_csv(csv_file)
            # tokenize all texts
            # pad/truncate to max_length
            # store as self.encoded_texts (list of Tensors)
            # store labels as self.labels

        def __len__(self) -> int: ...
        def __getitem__(self, idx) -> tuple[Tensor, int]:
            # Returns (token_ids_tensor, label_int)

    Theory note: ch06 notes — "6.3 Creating data loaders"
```

---

### 4.3 Classification model setup

```
[ ] Task: Modify GPTModel for classification

    # Load pretrained GPT-2 small:
    model = GPTModel(BASE_CONFIG)
    load_weights_into_gpt(model, params)

    # Step 1 — freeze ALL parameters:
    for param in model.parameters():
        param.requires_grad = False

    # Step 2 — replace output head:
    model.out_head = nn.Linear(
        in_features=BASE_CONFIG["emb_dim"],  # 768
        out_features=2                        # num_classes
    )

    # Step 3 — unfreeze last block + final LayerNorm:
    for param in model.trf_blocks[-1].parameters():
        param.requires_grad = True
    for param in model.final_norm.parameters():
        param.requires_grad = True

    # Verify trainable param count:
    # total   ≈ 124M params
    # trainable should be ≈ 7.4M (last block + norm + new head)

    Theory note: ch06 notes — "6.5 Adding a classification head"
```

---

### 4.4 Classification accuracy

```
[ ] Task: Compute accuracy over a DataLoader

    def calc_accuracy_loader(
        data_loader: DataLoader,
        model: GPTModel,
        device: torch.device,
        num_batches: int = None
    ) -> float:
        """
        For each batch: forward pass → logits[:, -1, :] (last token position)
        → argmax → compare with labels.
        Returns: fraction correct (0.0 – 1.0)
        Use torch.no_grad().
        """

    # Note: use LAST token position for the class logit — not first or mean

    Theory note: ch06 notes — "6.6 Evaluating the model" +
                               "6.5 Why last token?"
```

---

### 4.5 Classification training loop

```
[ ] Task: Fine-tuning loop for classification

    def train_classifier_simple(
        model: GPTModel,
        train_loader: DataLoader,
        val_loader: DataLoader,
        optimizer: torch.optim.Optimizer,
        device: torch.device,
        num_epochs: int,
        eval_freq: int,
        eval_iter: int
    ) -> tuple[list, list, list, list, int]:
        """
        Like train_model_simple but:
          - loss = F.cross_entropy(logits[:, -1, :], labels)
          - also track accuracy with calc_accuracy_loader
        Returns: (train_losses, val_losses, train_accs, val_accs, examples_seen)
        """

    # Recommended hyperparams:
    # optimizer = AdamW(model.parameters(), lr=5e-5, weight_decay=0.1)
    # num_epochs = 5

    Theory note: ch06 notes — "6.7 Fine-tuning the model"
```

---

### 4.6 Inference wrapper

```
[ ] Task: Single-text classification function

    def classify_review(
        text: str,
        model: GPTModel,
        tokenizer,
        device: torch.device,
        max_length: int = None,
        pad_token_id: int = 50256
    ) -> str:
        """
        Tokenise → truncate/pad → forward pass → argmax on last token logit.
        Returns: "spam" or "not spam"
        """

    Theory note: ch06 notes — "6.8 Using the LLM as spam classifier"
```

---

## PHASE 5 — Instruction Fine-Tuning (Ch. 7)

> Target: GPT-2 medium (355M).

### 5.1 Download and format instruction dataset

```
[ ] Task: Load Alpaca-style JSON dataset

    def download_and_load_file(
        file_path: str,
        url: str
    ) -> list[dict]:
        """
        Download JSON if not cached, load and return as list of dicts.
        Each dict has keys: "instruction", "input" (optional), "output"
        Dataset: 1,100 instruction-response pairs
        """

    def format_input(entry: dict) -> str:
        """
        Format one entry into the Alpaca prompt template:

        Below is an instruction that describes a task. Write a response
        that appropriately completes the request.

        ### Instruction:
        {entry["instruction"]}

        ### Input:            ← only if entry["input"] is non-empty
        {entry["input"]}

        Returns: formatted string (WITHOUT the response)
        """

    Theory note: ch07 notes — "7.2 Preparing the instruction dataset"
```

---

### 5.2 Instruction dataset class

```
[ ] Task: Dataset that stores formatted+tokenised instruction pairs

    class InstructionDataset(Dataset):
        def __init__(
            self,
            data: list[dict],   # list of instruction entries
            tokenizer
        ):
            # For each entry: format_input(entry) + "\n\n### Response:\n" + entry["output"]
            # Tokenise the full formatted string
            # Store as self.encoded_texts (list of lists of ints)

        def __len__(self) -> int: ...
        def __getitem__(self, idx) -> list[int]:
            # Returns raw token id list (no padding here — done in collate)

    Theory note: ch07 notes — "7.2 / 7.3"
```

---

### 5.3 Custom collate function

```
[ ] Task: Batch variable-length sequences with instruction masking

    def custom_collate_fn(
        batch: list[list[int]],       # list of token-id lists (different lengths)
        pad_token_id: int = 50256,
        ignore_index: int = -100,     # what cross_entropy ignores
        allowed_max_length: int = None,
        device: str = "cpu"
    ) -> tuple[Tensor, Tensor]:
        """
        1. Find longest sequence in batch, pad all others to match.
        2. inputs  = padded sequences (all tokens)
        3. targets = inputs shifted right by 1, pad positions set to ignore_index
        4. MASK instruction tokens in targets: set to ignore_index
           (only compute loss on the response tokens, not the prompt)
        5. Truncate to allowed_max_length if set.
        Returns: (inputs_tensor, targets_tensor) both shape (batch, max_len)
        """

    # Use functools.partial to bind device before passing to DataLoader:
    # from functools import partial
    # collate = partial(custom_collate_fn, device=device, allowed_max_length=1024)

    Theory note: ch07 notes — "7.3 Organizing data into training batches"
```

---

### 5.4 Instruction DataLoaders

```
[ ] Task: Build train/val/test loaders for instruction data

    def create_instruction_dataloaders(
        data: list[dict],
        tokenizer,
        device: torch.device,
        batch_size: int = 8,
        train_frac: float = 0.85,
        val_frac: float = 0.05
    ) -> tuple[DataLoader, DataLoader, DataLoader]:
        """
        Split data → train/val/test.
        Create InstructionDataset for each split.
        Wrap with DataLoader using custom_collate_fn.
        Returns: (train_loader, val_loader, test_loader)
        """

    Theory note: ch07 notes — "7.4 Creating data loaders"
```

---

### 5.5 Load GPT-2 medium (355M)

```
[ ] Task: Same weight loading as 3.8 but for the 355M model

    CHOOSE_MODEL = "gpt2-medium (355M)"

    BASE_CONFIG = {
        "vocab_size":     50257,
        "context_length": 1024,
        "drop_rate":      0.0,    # disabled for fine-tuning
        "qkv_bias":       True,
        "emb_dim":        1024,
        "n_layers":       24,
        "n_heads":        16,
    }

    settings, params = download_and_load_gpt2(model_size="355M", models_dir="gpt2")
    model = GPTModel(BASE_CONFIG)
    load_weights_into_gpt(model, params)
    model.eval()

    # Verify: generate a coherent response to a simple instruction
    # before any fine-tuning — should produce text completion, NOT
    # instruction-following (that's the point of fine-tuning)

    Theory note: ch07 notes — "7.5 Loading a pretrained LLM"
```

---

### 5.6 Instruction fine-tuning loop

```
[ ] Task: Fine-tune on instruction data (same loop structure as pretraining)

    def train_model_instruction(
        model: GPTModel,
        train_loader: DataLoader,
        val_loader: DataLoader,
        optimizer: torch.optim.Optimizer,
        device: torch.device,
        num_epochs: int,
        eval_freq: int,
        eval_iter: int,
        start_context: str,
        tokenizer
    ) -> tuple[list, list, list]:
        """
        Identical structure to train_model_simple (Phase 3.5).
        Loss is still cross_entropy but ignore_index=-100 is now essential —
        the -100 masked positions (instruction tokens) are automatically
        skipped by F.cross_entropy.
        Returns: (train_losses, val_losses, tokens_seen)
        """

    # Recommended hyperparams:
    # optimizer = AdamW(model.parameters(), lr=0.00005, weight_decay=0.1)
    # num_epochs = 2
    # eval_freq  = 5

    Theory note: ch07 notes — "7.6 Fine-tuning the LLM on instruction data"
```

---

### 5.7 Extract and save model responses

```
[ ] Task: Run fine-tuned model on test set, save responses to JSON

    def generate_model_response(
        prompt: str,
        model: GPTModel,
        tokenizer,
        device: torch.device,
        max_new_tokens: int = 256
    ) -> str:
        """
        Tokenise prompt → generate(temperature=0, top_k=1)
        → decode → extract ONLY the response part (after "### Response:\n")
        Returns: response string only
        """

    # Save loop:
    # for entry in test_data:
    #     prompt   = format_input(entry)
    #     response = generate_model_response(prompt, ...)
    #     entry["model_response"] = response
    # with open("instruction-data-with-response.json", "w") as f:
    #     json.dump(test_data, f, indent=4)

    Theory note: ch07 notes — "7.7 Extracting and saving responses"
```

---

### 5.8 LLM-as-judge evaluation

```
[ ] Task: Automated evaluation using Ollama (Llama 3)

    def query_model(
        prompt: str,
        model_name: str = "llama3",
        url: str = "http://localhost:11434/api/chat"
    ) -> str:
        """
        POST to local Ollama server.
        Payload: {"model": model_name, "messages": [{"role":"user","content":prompt}]}
        Returns: response text string
        """

    def evaluate_with_llm_judge(
        test_data: list[dict],
        eval_model: str = "llama3"
    ) -> float:
        """
        For each entry in test_data:
          Build a scoring prompt asking Llama 3 to rate the model response
          compared to the reference answer on a scale of 0-100.
          Parse the numeric score from the response.
        Returns: average score across all test entries
        """

    # Prerequisites:
    # 1. Install Ollama: https://ollama.com
    # 2. Run: ollama pull llama3  (4.7 GB download)
    # 3. Start: ollama serve

    Theory note: ch07 notes — "7.8 Evaluating the fine-tuned LLM"
```

---

## PHASE 6 — Stretch Goals (Post-pipeline)

```
[ ] 6.1  Plot training curves — loss and accuracy vs tokens_seen
         Use matplotlib or Chart.js; compare train vs val

[ ] 6.2  LoRA fine-tuning (Exercise 7.4 from book)
         Replace full fine-tuning loop with LoRA adapter layers
         Compare: training time, GPU memory, final evaluation score
         Theory note: ch07 notes — Appendix E + Exercise 7.4

[ ] 6.3  DPO preference tuning
         Use the ch07/04_preference-tuning-with-dpo/ bonus code as guide
         Requires: a preference dataset (instruction + chosen + rejected responses)
         Theory note: ch07 notes — "9: Conclusions / DPO"

[ ] 6.4  Swap in your own domain dataset for instruction fine-tuning
         (e.g., Assamese language, medical summaries, code review)
         Only Phase 5 changes — architecture and training loop stay identical
```

---

## Reference: Chapter → Note File Mapping

| Chapter | Topic                       | Your note file                                  |
| ------- | --------------------------- | ----------------------------------------------- |
| Ch. 2   | Tokenization, DataLoader    | `ch02-working-with-text-data.md`                |
| Ch. 3   | Attention mechanisms        | `ch03-coding-attention-mechanisms.md`           |
| Ch. 4   | GPT architecture            | `ch04-implementing-a-gpt-model-from-scratch.md` |
| Ch. 5   | Pretraining, weight loading | `ch05-pretraining-on-unlabeled-data.md`         |
| Ch. 6   | Classification fine-tuning  | `ch06-fine-tuning-for-classification.md`        |
| Ch. 7   | Instruction fine-tuning     | `ch07-fine-tuning-to-follow-instructions.md`    |

---

## Key config values to memorise

| Model        | emb_dim | n_heads | n_layers | Params |
| ------------ | ------- | ------- | -------- | ------ |
| GPT-2 small  | 768     | 12      | 12       | 124M   |
| GPT-2 medium | 1024    | 16      | 24       | 355M   |
| GPT-2 large  | 1280    | 20      | 36       | 774M   |
| GPT-2 XL     | 1600    | 25      | 48       | 1558M  |

---

_Total tasks: 30 core + 4 stretch. Estimated time at steady pace: 3–4 weeks._
