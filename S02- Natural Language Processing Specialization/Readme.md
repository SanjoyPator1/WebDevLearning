# Natural Language Processing Specialization - Complete Guide

## Overview

The Natural Language Processing Specialization is a 4-course series that covers the fundamentals of NLP through advanced attention models. This comprehensive program progresses from basic text classification to modern transformer architectures.

**Total Duration**: 110 hours across 4 courses
**Specialization Focus**: Building practical NLP systems from classification to advanced language models

---

## Course Structure

### Course 1: Natural Language Processing with Classification and Vector Spaces

**Duration**: 33 hours | **Focus**: Foundation concepts and vector representations

### Course 2: Natural Language Processing with Probabilistic Models

**Duration**: 30 hours | **Focus**: Statistical approaches and hidden markov models

### Course 3: Natural Language Processing with Sequence Models

**Duration**: 21 hours | **Focus**: RNNs, LSTMs, and neural sequence modeling

### Course 4: Natural Language Processing with Attention Models

**Duration**: 26 hours | **Focus**: Attention mechanisms and transformer architectures

---

# Course 1: Natural Language Processing with Classification and Vector Spaces

## Week 1: Sentiment Analysis with Logistic Regression

**Duration**: 1h 18m videos, 1h 42m readings, 1 programming assignment

### Learning Objectives

Extract features from text into numerical vectors, then build a binary classifier for tweets using logistic regression.

### Content Structure

#### Lecture: Logistic Regression

- Welcome to the NLP Specialization (4 min)
- Welcome to Course 1 (1 min)
- Acknowledgement - Ken Church (10 min reading)
- Week Introduction (35 sec)

#### Supervised ML & Sentiment Analysis

- Supervised ML & Sentiment Analysis (2 min + 2 min reading)
- Vocabulary & Feature Extraction (2 min + 2 min reading)
- Negative and Positive Frequencies (2 min)
- Feature Extraction with Frequencies (2 min + 10 min reading)

#### Preprocessing

- Preprocessing (3 min + 10 min reading)
- **Lab**: Natural Language preprocessing (1 hour)
- Putting it All Together (2 min + 10 min reading)
- **Lab**: Visualizing word frequencies (1 hour)

#### Logistic Regression Deep Dive

- Logistic Regression Overview (3 min + 10 min reading)
- Logistic Regression: Training (1 min + 10 min reading)
- **Lab**: Visualizing tweets and Logistic Regression models (1 hour)
- Logistic Regression: Testing (4 min + 10 min reading)
- Logistic Regression: Cost Function (5 min + 10 min reading)

#### Additional Resources

- Week Conclusion (30 sec)
- Optional Logistic Regression: Gradient (10 min reading)
- Intake Survey (1 min)
- Forum Information (2 min reading)
- Lecture Notes W1 (1 min reading)

## Week 2: Naive Bayes

**Duration**: 44 min videos, 1h 51m readings, 1 programming assignment

### Learning Objectives

Learn Bayes' rule for conditional probabilities and apply it to build a Naive Bayes tweet classifier.

### Content Structure

#### Lecture: Naive Bayes

- Week Introduction (27 sec)
- Probability and Bayes' Rule (3 min + 10 min reading)
- Bayes' Rule (4 min + 10 min reading)
- Naïve Bayes Introduction (5 min + 10 min reading)

#### Advanced Concepts

- Laplacian Smoothing (2 min + 10 min reading)
- Log Likelihood, Part 1 (6 min + 10 min reading)
- Log Likelihood, Part 2 (2 min + 10 min reading)
- Training Naïve Bayes (3 min + 10 min reading)

#### Labs and Applications

- **Lab**: Visualizing likelihoods and confidence ellipses (1 hour)
- Testing Naïve Bayes (4 min + 10 min reading)
- Applications of Naïve Bayes (3 min + 10 min reading)
- Naïve Bayes Assumptions (3 min + 10 min reading)
- Error Analysis (3 min + 10 min reading)

#### Assessment

- Week Conclusion (44 sec)
- Lecture Notes W2 (1 min reading)
- **Practice Quiz**: Naive Bayes (30 min)
- **Programming Assignment**: Naive Bayes (3 hours)

## Week 3: Vector Space Models

**Duration**: 28 min videos, 1h 31m readings, 1 programming assignment

### Learning Objectives

Learn how vector space models capture semantic meaning and relationships between words. Create word vectors and visualize relationships using PCA.

### Content Structure

#### Lecture: Vector Space Models

- Week Introduction (47 sec)
- Vector Space Models (2 min + 10 min reading)
- Word by Word and Word by Doc (4 min + 10 min reading)
- **Lab**: Linear algebra in Python with Numpy (1 hour)

#### Distance and Similarity Metrics

- Euclidean Distance (3 min + 10 min reading)
- Cosine Similarity: Intuition (2 min + 10 min reading)
- Cosine Similarity (3 min + 10 min reading)
- Manipulating Words in Vector Spaces (3 min + 10 min reading)
- **Lab**: Manipulating word embeddings (1 hour)

#### Dimensionality Reduction

- Visualization and PCA (3 min + 10 min reading)
- PCA Algorithm (3 min + 10 min reading)
- **Lab**: Another explanation about PCA (1 hour)
- The Rotation Matrix (10 min optional reading)

#### Assessment

- Week Conclusion (46 sec)
- Lecture Notes W3 (1 min reading)
- **Practice Quiz**: Vector Space Models (30 min)
- **Programming Assignment**: Vector Space Models (3 hours)

## Week 4: Machine Translation and Locality Sensitive Hashing

**Duration**: 1h 8m videos, 1h 33m readings, 1 programming assignment

### Learning Objectives

Transform word vectors and assign them to subsets using locality sensitive hashing for machine translation and document search.

### Content Structure

#### Lecture: Machine Translation

- Week Introduction (46 sec)
- Overview (1 min)
- Transforming word vectors (7 min + 10 min reading)
- **Lab**: Rotation matrices in R2 (1 hour)

#### Nearest Neighbors and Hashing

- K-nearest neighbors (3 min + 10 min reading)
- Hash tables and hash functions (3 min + 10 min reading)
- Locality sensitive hashing (5 min + 10 min reading)
- Multiple Planes (3 min + 10 min reading)
- **Lab**: Hash tables (1 hour)

#### Search Applications

- Approximate nearest neighbors (3 min + 10 min reading)
- Searching documents (1 min + 10 min reading)

#### Final Resources

- Week Conclusion (50 sec)
- Lecture Notes W4 (1 min reading)
- **Practice Quiz**: Hashing and Machine Translation (30 min)
- End of access to Lab Notebooks (2 min reading)
- **Programming Assignment**: Word Translation (3 hours)
- Acknowledgements (10 min reading)
- Bibliography (10 min reading)
- **Heroes of NLP**: Andrew Ng with Kathleen McKeown (35 min)

---

# Course 2: Natural Language Processing with Probabilistic Models

## Week 1: Autocorrect and Minimum Edit Distance

**Duration**: 31 min videos, 39 min readings, 1 programming assignment

### Learning Objectives

Learn about autocorrect, minimum edit distance, and dynamic programming to build a spellchecker.

### Content Structure

#### Introduction

- Intro to Course 2 (1 min)
- Week Introduction (55 sec)
- Overview (1 min + 3 min reading)

#### Autocorrect Systems

- Autocorrect (2 min + 4 min reading)
- Building the model (4 min + 3 min reading)
- **Lab**: Building the vocabulary (1 hour)
- Building the model II (3 min + 4 min reading)
- **Lab**: Candidates from edits (1 hour)

#### Minimum Edit Distance

- Minimum edit distance (3 min + 5 min reading)
- Minimum edit distance algorithm (5 min + 3 min reading)
- Minimum edit distance algorithm II (4 min + 5 min reading)
- Minimum edit distance algorithm III (3 min + 4 min reading)

#### Assessment

- Week Conclusion (51 sec)
- Forum Information (2 min reading)
- Lecture Notes W1 (1 min reading)
- **Practice Quiz**: Auto-correct and Minimum Edit Distance (30 min)
- Workspace Information (5 min reading)
- **Programming Assignment**: Autocorrect (3 hours)

## Week 2: Part of Speech Tagging

**Duration**: 42 min videos, 1h 6m readings, 1 programming assignment

### Learning Objectives

Learn about Markov chains and Hidden Markov models to create part-of-speech tags for text corpus.

### Content Structure

#### Introduction to POS Tagging

- Week Introduction (1 min)
- Part of Speech Tagging (2 min + 4 min reading)
- **Lab**: Working with text files (20 min)

#### Markov Chains

- Markov Chains (3 min + 3 min reading)
- Markov Chains and POS Tags (4 min + 6 min reading)
- Hidden Markov Models (3 min + 6 min reading)

#### Probability Calculations

- Calculating Probabilities (3 min + 5 min reading)
- Populating the Transition Matrix (4 min + 6 min reading)
- Populating the Emission Matrix (2 min + 5 min reading)
- **Lab**: Working with tags and Numpy (20 min)

#### Viterbi Algorithm

- The Viterbi Algorithm (4 min + 5 min reading)
- Viterbi: Initialization (2 min + 5 min reading)
- Viterbi: Forward Pass (2 min + 10 min reading)
- Viterbi: Backward Pass (5 min + 10 min reading)

#### Assessment

- Week Conclusion (1 min)
- Lecture Notes W2 (1 min reading)
- **Practice Quiz**: Part of Speech Tagging (30 min)
- **Programming Assignment**: Part of Speech Tagging (3 hours)

## Week 3: Autocomplete and Language Models

**Duration**: 53 min videos, 1h 10m readings, 1 programming assignment

### Learning Objectives

Learn N-gram language models by calculating sequence probabilities and build an autocomplete language model.

### Content Structure

#### Lecture: Autocomplete

- Week Introduction (1 min)
- N-Grams: Overview (3 min + 5 min reading)
- N-grams and Probabilities (7 min + 10 min reading)
- Sequence Probabilities (5 min + 6 min reading)
- Starting and Ending Sentences (8 min + 6 min reading)
- **Lab**: Corpus preprocessing for N-grams (1 hour)

#### Language Modeling

- The N-gram Language Model (6 min + 10 min reading)
- Language Model Evaluation (6 min)
- **Lab**: Building the language model (1 hour)
- Language Model Evaluation (10 min reading)

#### Advanced Topics

- Out of Vocabulary Words (4 min + 10 min reading)
- Smoothing (6 min + 10 min reading)
- **Lab**: Language model generalization (1 hour)

#### Summary

- Week Summary (1 min + 2 min reading)
- Week Conclusion (46 sec)
- Lecture Notes W3 (1 min reading)
- **Practice Quiz**: Autocomplete (30 min)
- **Programming Assignment**: Autocomplete (3 hours)

## Week 4: Word Embeddings

**Duration**: 1h 13m videos, 1h 30m readings, 1 programming assignment

### Learning Objectives

Learn how word embeddings carry semantic meaning and build a Continuous bag-of-words model using Shakespeare text.

### Content Structure

#### Introduction

- Week Introduction (1 min)
- Overview (2 min + reading)

#### Basic Representations

- Basic Word Representations (3 min + 5 min reading)
- Word Embeddings (3 min + 4 min reading)
- How to Create Word Embeddings (3 min + 4 min reading)
- Word Embedding Methods (3 min + 4 min reading)

#### CBOW Model

- Continuous Bag-of-Words Model (4 min + 3 min reading)
- Cleaning and Tokenization (4 min + 5 min reading)
- Sliding Window of Words in Python (3 min + 10 min reading)
- Transforming Words into Vectors (3 min + 2 min reading)
- **Lab**: Data Preparation (30 min)

#### Architecture

- Architecture of the CBOW Model (3 min + 4 min reading)
- Architecture Dimensions (3 min + 4 min reading)
- Architecture Dimensions 2 (2 min + 3 min reading)
- Architecture Activation Functions (4 min + 5 min reading)
- **Lab**: Intro to CBOW model (30 min)

#### Training

- Training Cost Function (4 min + 3 min reading)
- Training Forward Propagation (3 min + 3 min reading)
- Training Backpropagation and Gradient Descent (4 min + 4 min reading)
- **Lab**: Training the CBOW model (40 min)

#### Evaluation

- Extracting Word Embedding Vectors (3 min + 5 min reading)
- **Lab**: Word Embeddings (20 min)
- Evaluating Word Embeddings: Intrinsic Evaluation (3 min + 4 min reading)
- Evaluating Word Embeddings: Extrinsic Evaluation (2 min + 3 min reading)
- **Lab**: Word embeddings step by step (1 hour)

#### Conclusion

- Conclusion (1 min + 2 min reading)
- Week Conclusion (45 sec)
- Lecture Notes W4 (1 min reading)
- **Practice Assignment**: Word Embeddings (30 min)
- Lab Notebooks Access Reminder (2 min reading)
- **Programming Assignment**: Word Embeddings (3 hours)
- Acknowledgments (10 min reading)

---

# Course 3: Natural Language Processing with Sequence Models

## Week 1: Neural Networks and RNNs

**Duration**: 42 min videos, 1h 24m readings, 1 programming assignment

### Learning Objectives

Learn limitations of traditional language models and how RNNs and GRUs use sequential data for text prediction.

### Content Structure

#### Introduction to Neural Networks and TensorFlow

- Course 3 Introduction (3 min)
- Lesson Introduction (44 sec + 10 min clarification reading)
- Neural Networks for Sentiment Analysis (3 min + 7 min reading)
- Dense Layers and ReLU (2 min + 5 min reading)
- Embedding and Mean Layers (3 min + 3 min reading)
- **Lab**: Introduction to TensorFlow (30 min)
- Community Forum Information (10 min)

#### Practice Assignment

- Workspace Information (5 min reading)
- **Practice Assignment**: Sentiment with Deep Neural Networks (3 hours)

#### N-grams vs. Sequence Models

- Lesson Introduction (49 sec)
- Traditional Language models (3 min + 5 min reading)
- Recurrent Neural Networks (4 min + 4 min reading)
- Applications of RNNs (3 min + 3 min reading)
- Math in Simple RNNs (3 min + 6 min reading)
- **Lab**: Hidden State Activation (20 min)

#### RNN Implementation

- Cost Function for RNNs (2 min + 5 min reading)
- Implementation Note (1 min + 3 min reading)
- Gated Recurrent Units (4 min + 7 min reading)
- **Lab**: Vanilla RNNs, GRUs and the scan function (20 min)

#### Advanced RNNs

- Deep and Bi-directional RNNs (4 min + 10 min reading)
- Calculating Perplexity (10 min reading)
- **Lab**: Calculating Perplexity (20 min)

#### Assessment

- Week Conclusion (57 sec)
- Lecture Notes W1 (1 min reading)
- **Practice Quiz**: RNNs for Language Modelling (30 min)
- **Programming Assignment**: Deep N-grams (3 hours)

## Week 2: LSTMs and Named Entity Recognition

**Duration**: 25 min videos, 43 min readings, 1 programming assignment

### Learning Objectives

Learn how LSTMs solve vanishing gradient problems and build Named Entity Recognition systems.

### Content Structure

#### LSTMs and Named Entity Recognition

- Week Introduction (1 min)
- RNNs and Vanishing Gradients (6 min + 6 min reading)
- Intro to optimization in deep learning (10 min optional reading)
- **Lab**: Vanishing Gradients (15 min)

#### LSTM Architecture

- Introduction to LSTMs (4 min + 3 min reading)
- LSTM Architecture (3 min + 4 min reading)

#### Named Entity Recognition

- Introduction to Named Entity Recognition (3 min + 2 min reading)
- Training NERs: Data Processing (4 min + 5 min reading)
- Long Short-Term Memory Reference (10 min reading)
- Computing Accuracy (1 min + 2 min reading)

#### Assessment

- Week Conclusion (32 sec)
- Lecture Notes W2 (1 min reading)
- **Practice Quiz**: LSTMs and Named Entity Recognition (30 min)
- **Programming Assignment**: Named Entity Recognition (NER) (3 hours)

## Week 3: Siamese Networks

**Duration**: 34 min videos, 50 min readings, 1 programming assignment

### Learning Objectives

Learn about Siamese networks and build a network that identifies question duplicates.

### Content Structure

#### Siamese Networks

- Week Introduction (46 sec)
- Siamese Networks (2 min + 5 min reading)
- Architecture (3 min + 3 min reading)
- **Lab**: Creating a Siamese Model (20 min)

#### Cost Function and Training

- Cost Function (3 min + 6 min reading)
- Triplets (5 min + 6 min reading)
- Computing The Cost I (5 min + 6 min reading)
- Computing The Cost II (6 min + 5 min reading)
- **Lab**: Implementing the Modified Triplet Loss in TensorFlow (30 min)

#### Applications

- One Shot Learning (2 min + 4 min reading)
- Training / Testing (3 min + 4 min reading)
- **Lab**: Evaluate a Siamese Model (20 min)

#### Assessment

- Week Conclusion (37 sec)
- Lecture Notes W3 (1 min reading)
- **Practice Quiz**: Siamese Networks (30 min)
- **Programming Assignment**: Question Duplicates (3 hours)
- Acknowledgments (10 min reading)

---

# Course 4: Natural Language Processing with Attention Models

## Week 1: Neural Machine Translation

**Duration**: 1h 28m videos, 26 min readings, 1 programming assignment

### Learning Objectives

Discover shortcomings of seq2seq models and solve them with attention mechanisms for Neural Machine Translation.

### Content Structure

#### Neural Machine Translation

- Course 4 Introduction (2 min)
- Week Introduction (49 sec)
- Seq2seq (5 min)
- Seq2seq Model with Attention (5 min)
- **Lab**: Basic Attention (30 min)
- Background on seq2seq (10 min reading)

#### Attention Mechanisms

- Queries, Keys, Values, and Attention (5 min)
- **Lab**: Scaled Dot-Product Attention (30 min)
- Setup for Machine Translation (1 min)
- Teacher Forcing (2 min)
- NMT Model with Attention (3 min)

#### Evaluation Metrics

- BLEU Score (4 min)
- **Lab**: BLEU Score (30 min)
- ROUGE-N Score (5 min)

#### Decoding Strategies

- Sampling and Decoding (3 min)
- Beam Search (6 min)
- Minimum Bayes Risk (3 min)

#### Resources

- Week Conclusion (52 sec)
- Content Resource (10 min reading)
- Community Information (10 min)
- Lecture Notes W1 (1 min reading)
- **Practice Quiz**: Neural Machine Translation (30 min)
- Workspace Information (5 min reading)
- **Programming Assignment**: NMT with Attention (TensorFlow) (3 hours)
- **Heroes of NLP**: Andrew Ng with Oren Etzioni (34 min)

## Week 2: Text Summarization

**Duration**: 39 min videos, 51 min readings, 1 programming assignment

### Learning Objectives

Compare RNNs to Transformer architecture and create text summarization tools.

### Content Structure

#### Text Summarization

- Week Introduction (53 sec)
- Transformers vs RNNs (3 min + 10 min reading)
- Transformers overview (5 min)
- Transformer Applications (7 min + 10 min reading)

#### Attention Mechanisms

- Scaled and Dot-Product Attention (3 min)
- Masked Self Attention (3 min)
- Multi-head Attention (5 min + 10 min reading)
- **Lab**: Attention (1 hour)
- **Lab**: Masking (1 hour)
- **Lab**: Positional encoding (1 hour)

#### Transformer Architecture

- Transformer Decoder (4 min + 10 min reading)
- Transformer Summarizer (4 min)

#### Assessment

- Week Conclusion (34 sec)
- Content Resource (10 min reading)
- Lecture Notes W2 (1 min reading)
- **Practice Quiz**: Text Summarization (30 min)
- **Programming Assignment**: Transformer Summarizer (3 hours)

## Week 3: Question Answering

**Duration**: 1h 38m videos, 2h 16m readings, 1 programming assignment

### Learning Objectives

Explore transfer learning with T5 and BERT, then build a question answering model.

### Content Structure

#### Question Answering

- Week Introduction (41 sec)
- Week 3 Overview (6 min + 10 min reading)
- Transfer Learning in NLP (6 min + 10 min reading)
- ELMo, GPT, BERT, T5 (7 min + 10 min reading)

#### BERT Deep Dive

- Bidirectional Encoder Representations from Transformers (BERT) (4 min + 10 min reading)
- BERT Objective (2 min + 10 min reading)
- Fine tuning BERT (2 min + 10 min reading)

#### T5 and Training

- Transformer: T5 (3 min + 10 min reading)
- Multi-Task Training Strategy (5 min + 10 min reading)
- GLUE Benchmark (2 min + 10 min reading)
- **Lab**: SentencePiece and BPE (2 hours)

#### Hugging Face

- Welcome to Hugging Face 🤗 (10 min reading)
- Hugging Face Introduction (2 min)
- Hugging Face I (3 min)
- Hugging Face II (3 min)
- Hugging Face III (4 min)

#### Practical Implementation

- Week Conclusion (29 sec)
- **Lab**: Question Answering with HuggingFace - Using a base model (1 hour)
- **Lab**: Question Answering with HuggingFace 2 - Fine-tuning a model (1 hour)
- Content Resource (10 min reading)

#### Assessment

- Lecture Notes W3 (1 min reading)
- **Practice Quiz**: Question Answering (30 min)
- **Programming Assignment**: Question Answering (3 hours)
- **Heroes of NLP**: Andrew Ng with Quoc Le (40 min)

#### Final Resources

- Acknowledgments (10 min reading)
- References (10 min reading)
- Mentoring Opportunity (5 min optional reading)

---

## Key Takeaways

### Progressive Learning Path

1. **Course 1**: Foundation - Text classification, vector spaces, basic ML
2. **Course 2**: Probabilistic Models - Statistical approaches, Markov models
3. **Course 3**: Neural Sequences - RNNs, LSTMs, neural architectures
4. **Course 4**: Modern NLP - Attention, transformers, BERT, T5

### Practical Skills Developed

- Text preprocessing and feature extraction
- Building classification systems (logistic regression, naive bayes)
- Vector space models and word embeddings
- Sequence modeling with RNNs and LSTMs
- Attention mechanisms and transformer architecture
- Transfer learning with pre-trained models
- Real-world applications: sentiment analysis, machine translation, question answering

### Programming Tools

- Python and NumPy for mathematical operations
- TensorFlow for neural network implementation
- Hugging Face for pre-trained models
- Practical labs with real datasets

This specialization provides a comprehensive journey from traditional NLP techniques to cutting-edge transformer models, preparing students for modern NLP applications in industry and research.
