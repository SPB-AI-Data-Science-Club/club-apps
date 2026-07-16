# Art Style Transfer

Six artistic filters built from classical image-processing operations. No black box, every effect is readable code.

**Live demo:** [style.spbdatascience.org](https://style.spbdatascience.org)

## Features

- Pencil sketch, watercolor, oil painting, neon glow, mosaic, and vintage film
- Each filter is a composition of primitive operations: edge detection, color quantization, blur kernels, channel curves
- Instant server-side processing and one-click download

## Stack

Python, Flask, Pillow, NumPy

## Local development

```bash
pip install flask pillow numpy
python app.py
```
