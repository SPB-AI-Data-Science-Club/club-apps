# Language Model Playground

A character-level n-gram language model you can retune in real time. The ancestor of GPT, small enough to read in one sitting.

**Live demo:** [textgen.spbdatascience.org](https://textgen.spbdatascience.org)

## Features

- Three corpora: Shakespeare's plays, The Adventures of Sherlock Holmes, Grimms' Fairy Tales (all public domain)
- Context length slider (1 to 6 characters): watch output sharpen from letter soup to fluent pastiche to outright memorization
- Temperature slider (0.05 to 2.5) using the same exponent-rescaling rule as production LLM samplers
- Model stats per run: distinct contexts learned, average branching factor, dead-end restarts

## How it works

`build_model` slides a window over the corpus and maps every length-k context to a Counter of next characters. Generation seeds at a real sentence start, then repeatedly samples from the context's distribution with counts raised to `1/temperature`. When generation reaches a context that appeared only once and dies, it restarts at a fresh sentence and counts the event; the dead-end counter is a concrete, visible argument for why generalization beats lookup, which is the entire reason neural language models exist.

## Stack

Python (standard library only for the model), Flask

## Local development

```bash
pip install flask
python app.py
```

Corpus files ship in `corpora/`; all three texts are public domain.
