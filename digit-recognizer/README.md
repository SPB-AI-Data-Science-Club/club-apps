# Digit Recognizer

Draw a digit; a CNN trained on MNIST reads it in real time. 98.6% test accuracy, about 106k parameters, CPU inference in under 30 ms.

**Not currently deployed.** Runs locally; see Local development below.

## Features

- Live prediction while you draw, with the full softmax distribution over all ten classes
- Faithful MNIST preprocessing in the browser: strokes are cropped to their bounding box, scaled to 20x20, and pasted into a 28x28 field centered on the pixel center of mass, the same normalization used to build the original dataset
- A visible 28x28 preview of exactly what the network sees
- Model card in the sidebar: parameter count, test accuracy, per-request inference time

## How it works

`model_def.py` defines a small CNN (two 3x3 conv blocks, 16 and 32 filters, then a 64-unit head with dropout). `train.py` trains it for three epochs on MNIST with Adam and writes `model/digit_cnn.pt` plus accuracy metadata. The Flask app loads the weights once and serves `/api/predict`, which takes 784 floats and returns the distribution. Matching the training normalization at the preprocessing stage is what makes browser drawings work; skip the center-of-mass step and accuracy collapses.

## Stack

Python, PyTorch, Flask, Canvas API

## Local development

```bash
pip install flask torch torchvision numpy
python train.py   # writes model/digit_cnn.pt (~430 KB)
python app.py
```

Trained weights are not committed; `train.py` reproduces them in a few minutes on a laptop.
