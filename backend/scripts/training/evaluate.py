#!/usr/bin/env python
"""Evaluation script for palm vein model"""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import torch.nn.functional as F
import numpy as np
from sklearn.metrics import roc_curve, auc, precision_recall_curve
from scipy.optimize import brentq
from scipy.interpolate import interp1d

sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.training.dataset_loader import PalmVeinDataset, CrossSessionDataset, create_dataloaders
from scripts.training.train import PalmVeinEncoder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


def load_model(checkpoint_path: str, device: torch.device) -> PalmVeinEncoder:
    """Load trained model from checkpoint"""
    checkpoint = torch.load(checkpoint_path, map_location=device)

    # Extract model config
    model_config = checkpoint.get('model_config', {})
    embedding_dim = model_config.get('embedding_dim', 512)

    # Create model
    model = PalmVeinEncoder(embedding_dim=embedding_dim)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()

    logger.info(f"Loaded model from {checkpoint_path} (epoch {checkpoint.get('epoch', 'unknown')})")
    return model


def extract_embeddings(model: PalmVeinEncoder, dataloader: DataLoader, device: torch.device) -> Tuple[np.ndarray, List[str]]:
    """Extract embeddings for all samples in dataloader"""
    embeddings = []
    labels = []

    with torch.no_grad():
        for batch in dataloader:
            images = batch['image'].to(device)
            emb = model(images).cpu().numpy()
            embeddings.append(emb)
            labels.extend(batch['subject_id'])

    return np.vstack(embeddings), labels


def compute_verification_metrics(embeddings: np.ndarray, labels: List[str]) -> Dict:
    """Compute verification metrics (EER, AUC, etc.)"""
    n = len(embeddings)
    similarities = []
    true_labels = []

    # Compute all pairwise similarities
    for i in range(n):
        for j in range(i + 1, n):
            sim = np.dot(embeddings[i], embeddings[j])  # Already L2 normalized
            similarities.append(sim)
            true_labels.append(1 if labels[i] == labels[j] else 0)

    similarities = np.array(similarities)
    true_labels = np.array(true_labels)

    # ROC curve
    fpr, tpr, thresholds = roc_curve(true_labels, similarities)
    fnr = 1 - tpr

    # EER
    eer_idx = np.nanargmin(np.abs(fpr - fnr))
    eer = float((fpr[eer_idx] + fnr[eer_idx]) / 2)
    eer_threshold = float(thresholds[eer_idx])

    # AUC
    roc_auc = float(auc(fpr, tpr))

    # FPR at specific thresholds
    fpr_at_001 = float(fpr[np.argmax(fpr <= 0.001)]) if np.any(fpr <= 0.001) else 1.0
    fpr_at_01 = float(fpr[np.argmax(fpr <= 0.01)]) if np.any(fpr <= 0.01) else 1.0
    fpr_at_1 = float(fpr[np.argmax(fpr <= 0.1)]) if np.any(fpr <= 0.1) else 1.0

    # Precision-Recall
    precision, recall, pr_thresholds = precision_recall_curve(true_labels, similarities)
    pr_auc = float(auc(recall, precision))

    return {
        'eer': eer,
        'eer_threshold': eer_threshold,
        'auc': roc_auc,
        'fpr_at_0.1%': fpr_at_001,
        'fpr_at_1%': fpr_at_01,
        'fpr_at_10%': fpr_at_1,
        'pr_auc': pr_auc,
        'num_genuine': int(np.sum(true_labels)),
        'num_impostor': int(np.sum(1 - true_labels))
    }


def compute_identification_metrics(
    embeddings: np.ndarray,
    labels: List[str],
    gallery_loader: DataLoader,
    probe_loader: DataLoader,
    device: torch.device,
    model: PalmVeinEncoder
) -> Dict:
    """Compute identification metrics (Rank-1, Rank-5, CMC)"""
    # Extract gallery and probe embeddings
    gallery_emb, gallery_labels = extract_embeddings(model, gallery_loader, device)
    probe_emb, probe_labels = extract_embeddings(model, probe_loader, device)

    # Compute similarities
    similarities = probe_emb @ gallery_emb.T  # (n_probe, n_gallery)

    # Rank-k accuracy
    ranks = [1, 5, 10, 20]
    rank_accuracies = {}

    for k in ranks:
        correct = 0
        for i, probe_label in enumerate(probe_labels):
            # Get top-k gallery indices
            top_k_indices = np.argsort(similarities[i])[::-1][:k]
            top_k_labels = [gallery_labels[idx] for idx in top_k_indices]
            if probe_label in top_k_labels:
                correct += 1
        rank_accuracies[f'rank_{k}'] = correct / len(probe_labels)

    return rank_accuracies


def evaluate_cross_session(
    model: PalmVeinEncoder,
    session1_csv: str,
    session2_csv: str,
    device: torch.device,
    batch_size: int = 32
) -> Dict:
    """Evaluate cross-session performance"""
    # Session 1 as gallery (enrollment)
    gallery_ds = CrossSessionDataset(session1_csv, session=1)
    gallery_loader = DataLoader(gallery_ds, batch_size=batch_size, shuffle=False, num_workers=4)

    # Session 2 as probe (authentication)
    probe_ds = CrossSessionDataset(session2_csv, session=2)
    probe_loader = DataLoader(probe_ds, batch_size=batch_size, shuffle=False, num_workers=4)

    return compute_identification_metrics(
        None, None, gallery_loader, probe_loader, device, model
    )


def evaluate_cross_dataset(
    model: PalmVeinEncoder,
    train_dataset_csv: str,
    test_dataset_csv: str,
    device: torch.device,
    batch_size: int = 32
) -> Dict:
    """Evaluate cross-dataset generalization"""
    # Use all train data as gallery
    train_ds = PalmVeinDataset(train_dataset_csv, augment=False)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=False, num_workers=4)

    # Test on other dataset
    test_ds = PalmVeinDataset(test_dataset_csv, augment=False)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=4)

    return compute_identification_metrics(
        None, None, train_loader, test_loader, device, model
    )


def main():
    parser = argparse.ArgumentParser(description="Evaluate palm vein model")
    parser.add_argument('--model', type=str, required=True, help='Model checkpoint path')
    parser.add_argument('--test-data', type=str, required=True, help='Test metadata CSV')
    parser.add_argument('--gallery-data', type=str, help='Gallery metadata CSV (for cross-session/dataset)')
    parser.add_argument('--probe-data', type=str, help='Probe metadata CSV (for cross-session/dataset)')
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu')
    parser.add_argument('--output', type=str, default=None, help='Output JSON for results')
    parser.add_argument('--cross-session', action='store_true', help='Cross-session evaluation')
    parser.add_argument('--cross-dataset', action='store_true', help='Cross-dataset evaluation')
    args = parser.parse_args()

    device = torch.device(args.device)
    logger.info(f"Using device: {device}")

    # Load model
    model = load_model(args.model, device)

    results = {}

    if args.cross_session and args.gallery_data and args.probe_data:
        logger.info("Running cross-session evaluation...")
        results['cross_session'] = evaluate_cross_session(
            model, args.gallery_data, args.probe_data, device, args.batch_size
        )
        logger.info(f"Cross-session Rank-1: {results['cross_session'].get('rank_1', 'N/A')}")

    elif args.cross_dataset and args.gallery_data and args.test_data:
        logger.info("Running cross-dataset evaluation...")
        results['cross_dataset'] = evaluate_cross_dataset(
            model, args.gallery_data, args.test_data, device, args.batch_size
        )
        logger.info(f"Cross-dataset Rank-1: {results['cross_dataset'].get('rank_1', 'N/A')}")

    else:
        logger.info("Running standard verification evaluation...")
        test_ds = PalmVeinDataset(args.test_data, augment=False)
        test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=4)

        embeddings, labels = extract_embeddings(model, test_loader, device)
        results['verification'] = compute_verification_metrics(embeddings, labels)

        logger.info(f"EER: {results['verification']['eer']:.4f}")
        logger.info(f"AUC: {results['verification']['auc']:.4f}")
        logger.info(f"Threshold: {results['verification']['eer_threshold']:.4f}")

    # Save results
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")

    return results


if __name__ == "__main__":
    main()