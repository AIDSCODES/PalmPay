#!/usr/bin/env python
"""Quick pipeline test - runs one batch to verify everything works"""
import torch
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.training.dataset_loader import create_triplet_dataloader, create_dataloaders
from scripts.training.train import PalmVeinEncoder, TripletLoss

device = torch.device('cpu')

print("Testing dataset loading...")
train_loader = create_triplet_dataloader(
    "dataset/tongji/train.csv",
    batch_size=2,
    num_workers=0
)
print(f"Triplet dataset size: {len(train_loader.dataset)}")

# Test one batch
batch = next(iter(train_loader))
print(f"Batch keys: {batch.keys()}")
print(f"Anchor shape: {batch['anchor'].shape}")
print(f"Positive shape: {batch['positive'].shape}")
print(f"Negative shape: {batch['negative'].shape}")

# Test model
model = PalmVeinEncoder(backbone='resnet34', embedding_dim=512, pretrained=False)
model.to(device)
model.eval()

with torch.no_grad():
    anchor_emb = model(batch['anchor'].to(device))
    pos_emb = model(batch['positive'].to(device))
    neg_emb = model(batch['negative'].to(device))
    print(f"Embedding shape: {anchor_emb.shape}")
    print(f"Anchor norm: {torch.norm(anchor_emb, dim=1)}")

# Test loss
criterion = TripletLoss(margin=0.3)
loss = criterion(anchor_emb, pos_emb, neg_emb)
print(f"Triplet loss: {loss.item():.4f}")

# Test regular dataloaders
print("\nTesting regular dataloaders...")
train_loader, val_loader, test_loader = create_dataloaders(
    "dataset/tongji/metadata.csv",
    batch_size=2,
    augment_train=False,
    num_workers=0
)
batch = next(iter(train_loader))
print(f"Regular batch keys: {batch.keys()}")
print(f"Image shape: {batch['image'].shape}")
print(f"Subject IDs: {batch['subject_id']}")

print("\n✅ All pipeline components working!")