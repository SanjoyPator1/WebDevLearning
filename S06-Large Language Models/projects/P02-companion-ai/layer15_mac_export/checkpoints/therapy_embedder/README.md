---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- generated_from_trainer
- dataset_size:2888
- loss:MultipleNegativesRankingLoss
base_model: BAAI/bge-base-en-v1.5
widget:
- source_sentence: yes_comma_ found and trusted some nice people to lead me to my
    hotel
  sentences:
  - In general, I usually let the client decide when this should occur, sometimes
    with some clients it will be a joint agreement, but even in that case it should
    weigh mostly on what the client feels. In short, therapy ends when you feel your
    done.C
  - The relationship between yourself and your therapist is one based on trust, respect,
    and understanding. The best way to determine if a therapist is right for you is
    to ask. Does this therapist respect my journey? Does this therapist respect me
    as a human? Does this therapist understand the unique factors contributing to
    my mental health? Do I trust
  - Did you find anything interesting inside any of the buildings?
- source_sentence: My mother takes care of niece whom my sister abandoned. She calls
    me <DATE_TIME> complaining, but I don't want to hear it anymore.
  sentences:
  - 'Buy the book "Boundaries: Where You End and I Begin." Read it. Apply <URL>riously,
    I''m not joking. You''re not wrong to "not want to hear it anymore" but if you
    don''t maintain healthy boundaries, you will allow your family to make you feel
    guilty for "not wanting to hear it anymore". That''s not fair to <URL>ve a copy
    to your mom, too. No, I didn''t w'
  - What you are describing sounds like it may be a form of dissociation. Dissociation
    is our mind's way of disconnecting us from aspects of our experience in an attempt
    to protect us in overwhelming situations. It also sounds like you are noticing
    anxiety in certain situations. In working with a competent therapist, you may
    be able to gain insight int
  - That's awesome. Do the people you work with know it?
- source_sentence: I lived with this girl once and I trusted her. Found out I never
    should have.
  sentences:
  - Hi. Do you have any opportunity to work with a therapist? It sounds like it might
    be really great to explore these feelings. If you aren't able to, there are many
    awesome gender work books available that you could use to explore your thoughts
    and feelings. Also - google "ask a gender therapist" - so many amazing video blogs
    to answer many questions
  - 'The problem you describe sounds very wearing on your <URL>e there particular
    reasons for why you feel everyone hates you?Have you been in a clash of ideas
    or opinions and feel yourself in the minority viewpoint?Or does your sense of
    being shut out start within your own mind, as though you anticipate that others
    will not like what you say?If actual '
  - My girlfriend was cheating on me and I didn't know.
- source_sentence: My good childhood friend died suddenly as a teenager. I haven't
    seen him in <DATE_TIME> and haven't talked to him in <DATE_TIME> yet somehow this
    hurts me more than I could ever imagine. It's been <DATE_TIME> since his passing,
    and I'm still not sure how to cope with this.
  sentences:
  - People often care deeply for those whom they love. I don't know how long you have
    been together. It is also common to want to be very closely connected to people
    who are important to <URL> may be helpful to have a conversation about talking
    more or talking about how you feel when he is not there and how he feels about
    answering you right away. It m
  - A PTSD diagnosis requires an event which occurred <DATE_TIME> prior to the symptoms.
    Depression is a common symptom of PTSD, but depression can come from many other
    sources as well. In the end, diagnoses are systems of behavioral labels. If you
    believe that one label (PTSD) is worse than another (Depression), you are creating
    a false hierarchy. Con
  - 'I am truly sorry for your loss.His passing has triggered some uneasy emotions.
    Do you know what these emotions are as you are trying to cope? Be aware, that
    "coping" is not processing. Coping means that the problem is always there, and
    you are "managing" rather than healing. And, as you know, that isn''t working.Emotional
    pain comes in waves, which '
- source_sentence: I just lost my grandpa and i'm having a rough time with it. I need
    some help to deal with the loss, but I don’t think I can pay for counseling. Where
    Can I get help?
  sentences:
  - 'Hi Bend, You''re scared, right? That makes sense. Each time we have a break-up
    we are a bit more in touch with how much is at stake in this whole love and relationship
    business. We are falling in love and letting someone close to our hearts and there''s
    a vulnerability in that; we can get hurt. Who you partner with long-term is a
    big decision and it '
  - There are lots of very good therapists out there–doing all types of therapy. However,
    studies show that more important than the type of therapy, the biggest indicator
    of client success is the therapeutic relationship that develops between the therapist
    and client. In other <URL>ere needs to be a ‘good fit’.
  - I am so sorry to hear about your loss. He must have been very special to you and
    it definitely makes sense that you are having a hard time with it. Counseling
    may be an option if you have a university near you with a graduate marriage and
    family therapist program. Graduate students provide counseling at a very low cost
    as part of their traineeship.
pipeline_tag: sentence-similarity
library_name: sentence-transformers
metrics:
- pearson_cosine
- spearman_cosine
model-index:
- name: SentenceTransformer based on BAAI/bge-base-en-v1.5
  results:
  - task:
      type: semantic-similarity
      name: Semantic Similarity
    dataset:
      name: therapy similarity
      type: therapy_similarity
    metrics:
    - type: pearson_cosine
      value: 0.9138139107209446
      name: Pearson Cosine
    - type: spearman_cosine
      value: 0.8913161304747291
      name: Spearman Cosine
---

# SentenceTransformer based on BAAI/bge-base-en-v1.5

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [BAAI/bge-base-en-v1.5](https://huggingface.co/BAAI/bge-base-en-v1.5). It maps sentences & paragraphs to a 768-dimensional dense vector space and can be used for retrieval.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [BAAI/bge-base-en-v1.5](https://huggingface.co/BAAI/bge-base-en-v1.5) <!-- at revision a5beb1e3e68b9ab74eb54cfd186867f64f240e1a -->
- **Maximum Sequence Length:** 512 tokens
- **Output Dimensionality:** 768 dimensions
- **Similarity Function:** Cosine Similarity
- **Supported Modality:** Text
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'transformer_task': 'feature-extraction', 'modality_config': {'text': {'method': 'forward', 'method_output_name': 'last_hidden_state'}}, 'module_output_name': 'token_embeddings', 'architecture': 'BertModel'})
  (1): Pooling({'embedding_dimension': 768, 'pooling_mode': 'cls', 'include_prompt': True})
  (2): Normalize({})
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```
Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    "I just lost my grandpa and i'm having a rough time with it. I need some help to deal with the loss, but I don’t think I can pay for counseling. Where Can I get help?",
    'I am so sorry to hear about your loss. He must have been very special to you and it definitely makes sense that you are having a hard time with it. Counseling may be an option if you have a university near you with a graduate marriage and family therapist program. Graduate students provide counseling at a very low cost as part of their traineeship.',
    "Hi Bend, You're scared, right? That makes sense. Each time we have a break-up we are a bit more in touch with how much is at stake in this whole love and relationship business. We are falling in love and letting someone close to our hearts and there's a vulnerability in that; we can get hurt. Who you partner with long-term is a big decision and it ",
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 768]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.6961, 0.2376],
#         [0.6961, 1.0000, 0.3793],
#         [0.2376, 0.3793, 1.0000]])
```
<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

## Evaluation

### Metrics

#### Semantic Similarity

* Dataset: `therapy_similarity`
* Evaluated with [<code>EmbeddingSimilarityEvaluator</code>](https://sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.sentence_transformer.evaluation.EmbeddingSimilarityEvaluator)

| Metric              | Value      |
|:--------------------|:-----------|
| pearson_cosine      | 0.9138     |
| **spearman_cosine** | **0.8913** |

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 2,888 training samples
* Columns: <code>sentence_0</code> and <code>sentence_1</code>
* Approximate statistics based on the first 100 samples:
  |          | sentence_0                                                                          | sentence_1                                                                         |
  |:---------|:------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------|
  | type     | string                                                                              | string                                                                             |
  | modality | text                                                                                | text                                                                               |
  | details  | <ul><li>min: 13 tokens</li><li>mean: 49.35 tokens</li><li>max: 101 tokens</li></ul> | <ul><li>min: 13 tokens</li><li>mean: 62.52 tokens</li><li>max: 98 tokens</li></ul> |
* Samples:
  | sentence_0                                                                                                                                                                                                                                             | sentence_1                                                                                                                                                                                                                                                                                                                                                                  |
  |:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
  | <code>My boyfriend shows affection, but I just push him away. Every time my boyfriend tries to kiss, hug, or touch me I almost always push him away. I'm on birth control and it has killed my sex drive. I love him so much. Why do I do this?</code> | <code>I sympathize with you! It is actually quite common for one partner to have a higher sex drive than the other, and can lead to discord in the relationship. The good news is, there are ways to deal with <URL> may have already answered your question. There are many medications that can alter one's sex drive. If your birth control pills are the cause o</code> |
  | <code>I don't know anyone and was alone so I wasn't sure if I should answer the door. Things are getting pretty scary in the world.</code>                                                                                                             | <code>I am having my first son in a couple of months.</code>                                                                                                                                                                                                                                                                                                                |
  | <code>I have major depression, severe, PTSD, anxiety disorder, and personality disorder. I had an appointment with my doctor. I was very upset, and I shared with him about that particular drug.</code>                                               | <code>Your doctor might be required to tell your psychiatrist - especially if your doctor is concerned about your <URL> was definitely a good thing that you told your primary care physician about what is going on. I know that must have been difficult to talk about with him. By having that conversation, you are helping your primary care physician and your</code> |
* Loss: [<code>MultipleNegativesRankingLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#multiplenegativesrankingloss) with these parameters:
  ```json
  {
      "scale": 20.0,
      "similarity_fct": "cos_sim",
      "gather_across_devices": false,
      "directions": [
          "query_to_doc"
      ],
      "partition_mode": "joint",
      "hardness_mode": null,
      "hardness_strength": 0.0
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 32
- `per_device_eval_batch_size`: 32
- `multi_dataset_batch_sampler`: round_robin

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `per_device_train_batch_size`: 32
- `num_train_epochs`: 3
- `max_steps`: -1
- `learning_rate`: 5e-05
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_steps`: 0
- `optim`: adamw_torch
- `optim_args`: None
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `optim_target_modules`: None
- `gradient_accumulation_steps`: 1
- `average_tokens_across_devices`: True
- `max_grad_norm`: 1
- `label_smoothing_factor`: 0.0
- `bf16`: False
- `fp16`: False
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `use_cache`: False
- `neftune_noise_alpha`: None
- `torch_empty_cache_steps`: None
- `auto_find_batch_size`: False
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `include_num_input_tokens_seen`: no
- `log_level`: passive
- `log_level_replica`: warning
- `disable_tqdm`: False
- `project`: huggingface
- `trackio_space_id`: None
- `trackio_bucket_id`: None
- `trackio_static_space_id`: None
- `per_device_eval_batch_size`: 32
- `prediction_loss_only`: True
- `eval_on_start`: False
- `eval_do_concat_batches`: True
- `eval_use_gather_object`: False
- `eval_accumulation_steps`: None
- `include_for_metrics`: []
- `batch_eval_metrics`: False
- `save_only_model`: False
- `save_on_each_node`: False
- `enable_jit_checkpoint`: False
- `push_to_hub`: False
- `hub_private_repo`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_always_push`: False
- `hub_revision`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `restore_callback_states_from_checkpoint`: False
- `full_determinism`: False
- `seed`: 42
- `data_seed`: None
- `use_cpu`: False
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `dataloader_prefetch_factor`: None
- `remove_unused_columns`: True
- `label_names`: None
- `train_sampling_strategy`: random
- `length_column_name`: length
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `ddp_static_graph`: None
- `ddp_backend`: None
- `ddp_timeout`: 1800
- `fsdp`: []
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `deepspeed`: None
- `debug`: []
- `skip_memory_metrics`: True
- `do_predict`: False
- `resume_from_checkpoint`: None
- `warmup_ratio`: None
- `local_rank`: -1
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: round_robin
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
| Epoch | Step | therapy_similarity_spearman_cosine |
|:-----:|:----:|:----------------------------------:|
| 1.0   | 91   | 0.8913                             |


### Training Time
- **Training**: 32.1 seconds

### Framework Versions
- Python: 3.10.12
- Sentence Transformers: 5.5.0
- Transformers: 5.8.1
- PyTorch: 2.5.1+cu121
- Accelerate: 1.13.0
- Datasets: 2.20.0
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

#### MultipleNegativesRankingLoss
```bibtex
@misc{oord2019representationlearningcontrastivepredictive,
      title={Representation Learning with Contrastive Predictive Coding},
      author={Aaron van den Oord and Yazhe Li and Oriol Vinyals},
      year={2019},
      eprint={1807.03748},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/1807.03748},
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->