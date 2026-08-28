# Photo Editor

Generates a high-quality, photorealistic image from a text prompt, optionally guided by a reference photo the visitor uploads.

**Not currently deployed.** Runs locally; see Local development below.

## What it does

Type a description of the photo you want and a diffusion model on the club's GPU servers renders it. Optionally upload a reference image and the prompt reshapes it (image-to-image), with an adjustable amount of change. Choose a square, portrait, or landscape shape.

## Model

[RealVisXL V5.0](https://huggingface.co/SG161222/RealVisXL_V5.0), a photorealistic SDXL fine-tune, runs in fp16 on the club's RTX 5080 with VAE slicing. Text-to-image and image-to-image share the loaded weights. A photo takes a few seconds.

## Architecture

The Flask app on the VPS validates the prompt and optional upload and submits a job to a queue on the club's GPU worker over a private Tailscale network. The client polls for status and retrieves the finished image. When the worker is offline the UI reports it.

## Responsible use

Generated photos can look real, which is why media literacy matters. The page asks users not to create realistic images of real people without consent and not to produce harmful, explicit, or deceptive content. Per-IP rate limits apply.

## Stack

Python, Flask, RealVisXL (SDXL) on a GPU worker, Tailscale

## Local development

```bash
pip install flask requests
python app.py
```
