#!/usr/bin/env python
"""Training script for palm vein embedding model"""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.training.dataset_loader import (
    PalmVeinDataset,
    TripletDataset,
    CrossSessionDataset,
    create_dataloaders,
    create_triplet_dataloader
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


class PalmVeinEncoder(nn.Module):
    """Palm vein embedding encoder"""

    def __init__(
        self,
        backbone: str = "resnet50",
        embedding_dim: int = 512,
        pretrained: bool = True,
        dropout: float = 0.1
    ):
        super().__init__()

        # Load backbone
        if backbone == "resnet50":
            from torchvision.models import resnet50, ResNet50_Weights
            weights = ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
            self.backbone = resnet50(weights=weights)
            backbone_dim = 2048
        elif backbone == "resnet34":
            from torchvision.models import resnet34, ResNet34_Weights
            weights = ResNet34_Weights.IMAGENET1K_V1 if pretrained else None
            self.backbone = resnet34(weights=weights)
            backbone_dim = 512
        elif backbone == "efficientnet_b0":
            from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
            weights = EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
            self.backbone = efficientnet_b0(weights=weights)
            backbone_dim = 1280
        elif backbone == "mobilenet_v3_small":
            from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
            weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
            self.backbone = mobilenet_v3_small(weights=weights)
            backbone_dim = 576
        else:
            raise ValueError(f"Unknown backbone: {backbone}")

        # Remove classification head
        if hasattr(self.backbone, 'fc'):
            self.backbone.fc = nn.Identity()
        elif hasattr(self.backbone, 'classifier'):
            self.backbone.classifier = nn.Identity()

        # Embedding head
        self.embedding_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(backbone_dim, embedding_dim),
            nn.BatchNorm1d(embedding_dim)
        )

        self.embedding_dim = embedding_dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass returning L2-normalized embedding"""
        features = self.backbone(x)
        embedding = self.embedding_head(features)
        embedding = F.normalize(embedding, p=2, dim=1)
        return embedding


class TripletLoss(nn.Module):
    """Triplet loss with margin"""

    def __init__(self, margin: float = 0.3):
        super().__init__()
        self.margin = margin

    def forward(self, anchor: torch.Tensor, positive: torch.Tensor, negative: torch.Tensor) -> torch.Tensor:
        """
        Args:
            anchor: (B, D)
            positive: (B, D)
            negative: (B, D)
        """
        pos_dist = F.pairwise_distance(anchor, positive, p=2)
        neg_dist = F.pairwise_distance(anchor, negative, p=2)

        loss = F.relu(pos_dist - neg_dist + self.margin)
        return loss.mean()


class ArcFaceLoss(nn.Module):
    """ArcFace loss for metric learning"""

    def __init__(self, num_classes: int, embedding_dim: int, margin: float = 0.5, scale: float = 64.0):
        super().__init__()
        self.num_classes = num_classes
        self.embedding_dim = embedding_dim
        self.margin = margin
        self.scale = scale

        self.weight = nn.Parameter(torch.FloatTensor(num_classes, embedding_dim))
        nn.init.xavier_uniform_(self.weight)

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Args:
            embeddings: (B, D) - L2 normalized
            labels: (B,) - class indices
        """
        # Normalize weights
        weight = F.normalize(self.weight, p=2, dim=1)

        # Cosine similarity
        cosine = F.linear(embeddings, weight)  # (B, C)

        # Add margin to target class
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1.0)

        theta = torch.acos(torch.clamp(cosine, -1.0 + 1e-7, 1.0 - 1e-7))
        target_theta = theta + self.margin
        target_cosine = torch.cos(target_theta)

        # Replace target class cosine with margined version
        output = cosine * (1 - one_hot) + target_cosine * one_hot
        output = output * self.scale

        return F.cross_entropy(output, labels)


class CosFaceLoss(nn.Module):
    """CosFace (Additive Margin) loss"""

    def __init__(self, num_classes: int, embedding_dim: int, margin: float = 0.35, scale: float = 64.0):
        super().__init__()
        self.num_classes = num_classes
        self.embedding_dim = embedding_dim
        self.margin = margin
        self.scale = scale

        self.weight = nn.Parameter(torch.FloatTensor(num_classes, embedding_dim))
        nn.init.xavier_uniform_(self.weight)

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        weight = F.normalize(self.weight, p=2, dim=1)
        cosine = F.linear(embeddings, weight)

        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1.0)

        output = cosine - one_hot * self.margin
        output = output * self.scale

        return F.cross_entropy(output, labels)


class PalmVeinTrainer:
    """Training manager for palm vein model"""

    def __init__(
        self,
        model: PalmVeinEncoder,
        train_loader: DataLoader,
        val_loader: DataLoader,
        test_loader: DataLoader,
        device: torch.device,
        loss_type: str = "triplet",
        margin: float = 0.3,
        learning_rate: float = 1e-4,
        weight_decay: float = 1e-4,
        num_classes: int = None
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.test_loader = test_loader
        self.device = device
        self.loss_type = loss_type

        # Optimizer
        self.optimizer = AdamW(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )

        # Scheduler
        self.scheduler = CosineAnnealingLR(self.optimizer, T_max=50)

        # Loss
        if loss_type == "triplet":
            self.criterion = TripletLoss(margin=margin)
            self.triplet_loader = create_triplet_dataloader(
                str(Path(train_loader.dataset.metadata_csv).parent / "train.csv") if hasattr(train_loader.dataset, 'metadata_csv') else None,
                batch_size=train_loader.batch_size
            ) if False else None  # Will create separately
        elif loss_type == "arcface":
            assert num_classes is not None, "num_classes required for ArcFace"
            self.criterion = ArcFaceLoss(num_classes, model.embedding_dim, margin=margin)
        elif loss_type == "cosface":
            assert num_classes is not None, "num_classes required for CosFace"
            self.criterion = CosFaceLoss(num_classes, model.embedding_dim, margin=margin)
        else:
            raise ValueError(f"Unknown loss type: {loss_type}")

        self.best_val_loss = float('inf')
        self.epoch = 0

    def train_epoch(self) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0.0
        num_batches = 0

        if self.loss_type == "triplet":
            # Need triplet dataloader
            for batch in self.train_loader:
                self.optimizer.zero_grad()

                anchor = batch['anchor'].to(self.device)
                positive = batch['positive'].to(self.device)
                negative = batch['negative'].to(self.device)

                anchor_emb = self.model(anchor)
                pos_emb = self.model(positive)
                neg_emb = self.model(negative)

                loss = self.criterion(anchor_emb, pos_emb, neg_emb)
                loss.backward()
                self.optimizer.step()

                total_loss += loss.item()
                num_batches += 1

        else:
            # ArcFace / CosFace - need subject labels
            for batch in self.train_loader:
                self.optimizer.zero_grad()

                images = batch['image'].to(self.device)
                labels = batch['subject_id'].to(self.device)  # Need label mapping

                embeddings = self.model(images)
                loss = self.criterion(embeddings, labels)

                loss.backward()
                self.optimizer.step()

                total_loss += loss.item()
                num_batches += 1

        return total_loss / max(num_batches, 1)

    def validate(self) -> float:
        """Validate model"""
        self.model.eval()
        total_loss = 0.0
        num_batches = 0

        with torch.no_grad():
            if self.loss_type == "triplet":
                for batch in self.val_loader:
                    anchor = batch['anchor'].to(self.device)
                    positive = batch['positive'].to(self.device)
                    negative = batch['negative'].to(self.device)

                    anchor_emb = self.model(anchor)
                    pos_emb = self.model(positive)
                    neg_emb = self.model(negative)

                    loss = self.criterion(anchor_emb, pos_emb, neg_emb)
                    total_loss += loss.item()
                    num_batches += 1
            else:
                for batch in self.val_loader:
                    images = batch['image'].to(self.device)
                    labels = batch['subject_id'].to(self.device)

                    embeddings = self.model(images)
                    loss = self.criterion(embeddings, labels)

                    total_loss += loss.item()
                    num_batches += 1

        return total_loss / max(num_batches, 1)

    def evaluate_verification(self, test_loader: DataLoader) -> Dict[str, float]:
        """Evaluate verification performance (EER, etc.)"""
        from sklearn.metrics import roc_curve, auc
        import numpy as np

        self.model.eval()
        embeddings = []
        labels = []

        with torch.no_grad():
            for batch in test_loader:
                images = batch['image'].to(self.device)
                emb = self.model(images).cpu().numpy()
                embeddings.append(emb)
                labels.extend(batch['subject_id'])

        embeddings = np.vstack(embeddings)
        labels = np.array(labels)

        # Compute pairwise similarities
        n = len(embeddings)
        similarities = []
        true_labels = []

        for i in range(n):
            for j in range(i + 1, n):
                sim = np.dot(embeddings[i], embeddings[j])  # Already L2 normalized
                similarities.append(sim)
                true_labels.append(1 if labels[i] == labels[j] else 0)

        similarities = np.array(similarities)
        true_labels = np.array(true_labels)

        # Compute EER
        fpr, tpr, thresholds = roc_curve(true_labels, similarities)
        fnr = 1 - tpr

        # Find EER point
        eer_idx = np.nanargmin(np.abs(fpr - fnr))
        eer = (fpr[eer_idx] + fnr[eer_idx]) / 2
        eer_threshold = thresholds[eer_idx]

        # AUC
        roc_auc = auc(fpr, tpr)

        return {
            'eer': float(eer),
            'eer_threshold': float(eer_threshold),
            'auc': float(roc_auc),
            'fpr_at_0.1%': float(fpr[np.argmax(fpr <= 0.001)]) if np.any(fpr <= 0.001) else 1.0
        }

    def save_checkpoint(self, path: str, metadata: Dict = None):
        """Save model checkpoint"""
        checkpoint = {
            'epoch': self.epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'best_val_loss': self.best_val_loss,
            'model_config': {
                'embedding_dim': self.model.embedding_dim,
                'backbone': self.model.__class__.__name__
            },
            'metadata': metadata or {}
        }
        torch.save(checkpoint, path)
        logger.info(f"Checkpoint saved to {path}")

    def load_checkpoint(self, path: str):
        """Load model checkpoint"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.epoch = checkpoint['epoch']
        self.best_val_loss = checkpoint['best_val_loss']
        logger.info(f"Checkpoint loaded from {path}")
        # Return next epoch to resume from
        return checkpoint['epoch'] + 1


def main():
    parser = argparse.ArgumentParser(description="Train palm vein embedding model")
    parser.add_argument('--data', type=str, default='dataset/combined/metadata.csv', help='Metadata CSV')
    parser.add_argument('--backbone', type=str, default='resnet50', choices=['resnet50', 'resnet34', 'efficientnet_b0', 'mobilenet_v3_small'])
    parser.add_argument('--embedding-dim', type=int, default=512)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--lr', type=float, default=1e-4)
    parser.add_argument('--loss', type=str, default='triplet', choices=['triplet', 'arcface', 'cosface'])
    parser.add_argument('--margin', type=float, default=0.3)
    parser.add_argument('--output', type=str, default='model/palm_vein_model.pt')
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu')
    parser.add_argument('--pretrained', action='store_true', default=True)
    parser.add_argument('--no-pretrained', dest='pretrained', action='store_false')
    parser.add_argument('--resume', type=str, default=None)
    args = parser.parse_args()

    device = torch.device(args.device)
    logger.info(f"Using device: {device}")

    # Create model
    model = PalmVeinEncoder(
        backbone=args.backbone,
        embedding_dim=args.embedding_dim,
        pretrained=args.pretrained
    )
    logger.info(f"Model: {args.backbone}, embedding_dim={args.embedding_dim}")

    # Create dataloaders
    if args.loss == "triplet":
        # Use triplet dataloader for training
        train_loader = create_triplet_dataloader(
            args.data,
            batch_size=args.batch_size,
            num_workers=0  # Set to 0 for Windows compatibility
        )
        # For validation, use regular dataset but we need triplet format
        val_loader = create_triplet_dataloader(
            str(Path(args.data).parent / "validation.csv"),
            batch_size=args.batch_size,
            num_workers=0
        )
        # For test evaluation, use regular dataset
        _, _, test_loader = create_dataloaders(
            args.data,
            batch_size=args.batch_size,
            augment_train=False,
            num_workers=0
        )
    else:
        train_loader, val_loader, test_loader = create_dataloaders(
            args.data,
            batch_size=args.batch_size,
            augment_train=True,
            num_workers=0
        )
    logger.info(f"Train: {len(train_loader.dataset)}, Val: {len(val_loader.dataset)}, Test: {len(test_loader.dataset)}")

    # Create trainer
    trainer = PalmVeinTrainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        test_loader=test_loader,
        device=device,
        loss_type=args.loss,
        margin=args.margin,
        learning_rate=args.lr,
        num_classes=len(train_loader.dataset.subject_ids) if hasattr(train_loader.dataset, 'subject_ids') else None
    )

    # Resume if specified
    start_epoch = 0
    if args.resume:
        start_epoch = trainer.load_checkpoint(args.resume)

    # Training loop
    for epoch in range(start_epoch, args.epochs):
        trainer.epoch = epoch

        train_loss = trainer.train_epoch()
        val_loss = trainer.validate()

        trainer.scheduler.step()

        logger.info(f"Epoch {epoch+1}/{args.epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | LR: {trainer.optimizer.param_groups[0]['lr']:.2e}")

        # Save best model
        if val_loss < trainer.best_val_loss:
            trainer.best_val_loss = val_loss
            trainer.save_checkpoint(
                args.output,
                metadata={
                    'epoch': epoch,
                    'val_loss': val_loss,
                    'train_loss': train_loss,
                    'args': vars(args)
                }
            )

    # Final evaluation
    logger.info("Evaluating on test set...")
    metrics = trainer.evaluate_verification(test_loader)
    logger.info(f"Test EER: {metrics['eer']:.4f} | AUC: {metrics['auc']:.4f} | Threshold: {metrics['eer_threshold']:.4f}")

    # Save final model with metadata
    final_output = args.output.replace('.pt', '_final.pt')
    trainer.save_checkpoint(final_output, metadata={
        'epoch': args.epochs - 1,
        'test_metrics': metrics,
        'args': vars(args)
    })

    logger.info("Training complete!")


if __name__ == "__main__":
    main()