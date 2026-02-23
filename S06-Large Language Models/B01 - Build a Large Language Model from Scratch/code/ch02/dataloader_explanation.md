## The Complete Data Loading Pipeline

This notebook presents the full data loading pipeline from Chapter 2 in consolidated form — all intermediate steps removed, only the final working code. It is the version you will reuse in upcoming chapters when training the GPT model.

### What the Pipeline Does

The pipeline takes raw text and produces input embeddings ready to be fed into the transformer. In one pass:

$$\text{Raw Text} \longrightarrow \text{Token IDs} \longrightarrow \text{Batched Tensors} \longrightarrow \text{Token Embeddings} + \text{Positional Embeddings} \longrightarrow X \in \mathbb{R}^{B \times L \times d}$$

where $B$ is the batch size, $L$ is the context length, and $d$ is the embedding dimension.

### The Dataset Class

```python
class GPTDatasetV1(Dataset):
    def __init__(self, txt, tokenizer, max_length, stride):
        self.input_ids = []
        self.target_ids = []

        token_ids = tokenizer.encode(txt, allowed_special={"<|endoftext|>"})

        for i in range(0, len(token_ids) - max_length, stride):
            input_chunk  = token_ids[i:i + max_length]
            target_chunk = token_ids[i + 1: i + max_length + 1]
            self.input_ids.append(torch.tensor(input_chunk))
            self.target_ids.append(torch.tensor(target_chunk))

    def __len__(self):
        return len(self.input_ids)

    def __getitem__(self, idx):
        return self.input_ids[idx], self.target_ids[idx]
```

`GPTDatasetV1` tokenizes the entire text once in `__init__`, then uses a sliding window of size `max_length` with step `stride` to pre-compute all input-target pairs. For a sequence of total length $N$, the number of windows is:

$$\text{windows} = \left\lfloor \frac{N - L}{S} \right\rfloor$$

where $L$ is `max_length` and $S$ is `stride`. Each window stores a pair of tensors of shape $(L,)$ — the input and its target shifted by one position.

### The DataLoader Factory

```python
def create_dataloader_v1(txt, batch_size, max_length, stride,
                         shuffle=True, drop_last=True, num_workers=0):
    tokenizer  = tiktoken.get_encoding("gpt2")
    dataset    = GPTDatasetV1(txt, tokenizer, max_length, stride)
    dataloader = DataLoader(
        dataset, batch_size=batch_size, shuffle=shuffle,
        drop_last=drop_last, num_workers=num_workers
    )
    return dataloader
```

This wraps the dataset in a PyTorch `DataLoader`. The key arguments are `drop_last=True`, which discards the final incomplete batch to avoid shape mismatches, and `shuffle=True`, which randomises sample order each epoch to help generalisation.

### Setting Up the Embedding Layers

```python
vocab_size     = 50257
output_dim     = 256
context_length = 1024

token_embedding_layer = torch.nn.Embedding(vocab_size, output_dim)
pos_embedding_layer   = torch.nn.Embedding(context_length, output_dim)
```

Two separate embedding layers are created. `token_embedding_layer` holds the weight matrix $W_E \in \mathbb{R}^{50257 \times 256}$ — one 256-dimensional vector per vocabulary entry. `pos_embedding_layer` holds $W_P \in \mathbb{R}^{1024 \times 256}$ — one 256-dimensional vector per possible position. Both are randomly initialised and will be updated during training.

### Creating the DataLoader

```python
batch_size = 8
max_length = 4

dataloader = create_dataloader_v1(
    raw_text,
    batch_size=batch_size,
    max_length=max_length,
    stride=max_length
)
```

Here `stride=max_length` means no overlap between windows — each consecutive batch covers a fresh, non-overlapping segment of text. This is the standard choice for training to avoid overfitting on repeated token positions.

### The Training Loop Skeleton

```python
for batch in dataloader:
    x, y = batch

    token_embeddings = token_embedding_layer(x)
    pos_embeddings   = pos_embedding_layer(torch.arange(max_length))

    input_embeddings = token_embeddings + pos_embeddings

    break
```

For each batch, `x` and `y` are both of shape $(B, L)$ — in this case $(8, 4)$. The embedding steps are:

**Step 1 — Token embeddings.** Each token ID in `x` is looked up in $W_E$, producing a tensor of shape $(B, L, d)$:

$$\text{token\_embeddings} = W_E[x] \in \mathbb{R}^{8 \times 4 \times 256}$$

**Step 2 — Positional embeddings.** `torch.arange(max_length)` generates position indices $[0, 1, 2, 3]$, which are looked up in $W_P$, producing a tensor of shape $(L, d)$:

$$\text{pos\_embeddings} = W_P[[0,1,2,3]] \in \mathbb{R}^{4 \times 256}$$

**Step 3 — Combined input embeddings.** The two tensors are added together. PyTorch broadcasts `pos_embeddings` of shape $(4, 256)$ across the batch dimension of `token_embeddings` of shape $(8, 4, 256)$:

$$X = \text{token\_embeddings} + \text{pos\_embeddings} \in \mathbb{R}^{8 \times 4 \times 256}$$

The same positional embedding is added to each of the 8 sequences in the batch, since all sequences share the same position indices $0$ through $L-1$.

### Output Shape

```python
print(input_embeddings.shape)
# torch.Size([8, 4, 256])
```

The final tensor $X$ has shape $(B, L, d) = (8, 4, 256)$. This is the input that the transformer receives. Each of the 8 sequences contains 4 token positions, and each position is represented as a 256-dimensional vector encoding both its identity and its location in the sequence.

---
