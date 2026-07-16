"""
Train the digit CNN on MNIST and save weights + metadata.
Run once on a development machine; only the weights are deployed.
"""
import json
import os

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from model_def import DigitCNN

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")
os.makedirs(MODEL_DIR, exist_ok=True)

EPOCHS = 3
tfm = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,)),
])

train_ds = datasets.MNIST(root="/tmp/mnist", train=True,  download=True, transform=tfm)
test_ds  = datasets.MNIST(root="/tmp/mnist", train=False, download=True, transform=tfm)
train_dl = DataLoader(train_ds, batch_size=128, shuffle=True)
test_dl  = DataLoader(test_ds,  batch_size=512)

model   = DigitCNN()
opt     = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.CrossEntropyLoss()

for epoch in range(EPOCHS):
    model.train()
    for i, (x, y) in enumerate(train_dl):
        opt.zero_grad()
        loss = loss_fn(model(x), y)
        loss.backward()
        opt.step()
        if i % 100 == 0:
            print(f"epoch {epoch+1}/{EPOCHS} batch {i}/{len(train_dl)} loss {loss.item():.4f}")

model.eval()
correct = 0
with torch.no_grad():
    for x, y in test_dl:
        correct += (model(x).argmax(1) == y).sum().item()
acc = correct / len(test_ds)
print(f"test accuracy: {acc:.4f}")

torch.save(model.state_dict(), os.path.join(MODEL_DIR, "digit_cnn.pt"))
with open(os.path.join(MODEL_DIR, "meta.json"), "w") as f:
    json.dump({
        "test_accuracy": round(acc, 4),
        "epochs":        EPOCHS,
        "trained_on":    "MNIST (60,000 images)",
    }, f)
print("saved model/digit_cnn.pt")
