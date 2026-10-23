#!/usr/bin/env python
"""Complete training pipeline orchestrator"""
import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(cmd: list, cwd: str = None) -> bool:
    """Run command and return success"""
    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed: {result.stderr}")
        return False
    logger.info(f"Command succeeded")
    return True


def step1_standardize_datasets(args):
    """Step 1: Standardize all datasets"""
    logger.info("=" * 60)
    logger.info("STEP 1: Standardize Datasets")
    logger.info("=" * 60)

    # This would call the standardize_datasets.py script
    # For now, just check if metadata files exist
    required_csvs = [
        "dataset/tongji/metadata.csv",
        "dataset/casia_ms/metadata.csv"
    ]

    for csv_path in required_csvs:
        if not Path(csv_path).exists():
            logger.warning(f"Missing: {csv_path} - run standardize_datasets.py first")
            return False

    logger.info("All metadata files present")
    return True


def step2_create_splits(args):
    """Step 2: Create train/val/test splits"""
    logger.info("=" * 60)
    logger.info("STEP 2: Create Dataset Splits")
    logger.info("=" * 60)

    # Combine and split
    cmd = [
        sys.executable, "scripts/training/standardize_datasets.py",
        "--combine",
        "--split"
    ]
    return run_command(cmd)


def step3_train_model(args):
    """Step 3: Train model"""
    logger.info("=" * 60)
    logger.info("STEP 3: Train Model")
    logger.info("=" * 60)

    cmd = [
        sys.executable, "scripts/training/train.py",
        "--data", "dataset/combined/metadata.csv",
        "--backbone", args.backbone,
        "--embedding-dim", str(args.embedding_dim),
        "--batch-size", str(args.batch_size),
        "--epochs", str(args.epochs),
        "--lr", str(args.lr),
        "--loss", args.loss,
        "--margin", str(args.margin),
        "--output", args.output,
        "--device", args.device
    ]

    if not args.pretrained:
        cmd.append("--no-pretrained")

    return run_command(cmd)


def step4_evaluate_model(args):
    """Step 4: Evaluate model"""
    logger.info("=" * 60)
    logger.info("STEP 4: Evaluate Model")
    logger.info("=" * 60)

    cmd = [
        sys.executable, "scripts/training/evaluate.py",
        "--model", args.output,
        "--test-data", "dataset/combined/test.csv",
        "--batch-size", str(args.batch_size),
        "--device", args.device,
        "--output", f"{args.output}_results.json"
    ]

    return run_command(cmd)


def step5_cross_session_eval(args):
    """Step 5: Cross-session evaluation"""
    logger.info("=" * 60)
    logger.info("STEP 5: Cross-Session Evaluation")
    logger.info("=" * 60)

    if not Path("dataset/tongji/train_session1.csv").exists():
        logger.warning("Cross-session splits not available, skipping")
        return True

    cmd = [
        sys.executable, "scripts/training/evaluate.py",
        "--model", args.output,
        "--cross-session",
        "--gallery-data", "dataset/tongji/train_session1.csv",
        "--probe-data", "dataset/tongji/test_session2.csv",
        "--batch-size", str(args.batch_size),
        "--device", args.device,
        "--output", f"{args.output}_cross_session.json"
    ]

    return run_command(cmd)


def step6_cross_dataset_eval(args):
    """Step 6: Cross-dataset evaluation"""
    logger.info("=" * 60)
    logger.info("STEP 6: Cross-Dataset Evaluation")
    logger.info("=" * 60)

    cmd = [
        sys.executable, "scripts/training/evaluate.py",
        "--model", args.output,
        "--cross-dataset",
        "--gallery-data", "dataset/tongji/metadata.csv",
        "--test-data", "dataset/casia_ms/metadata.csv",
        "--batch-size", str(args.batch_size),
        "--device", args.device,
        "--output", f"{args.output}_cross_dataset.json"
    ]

    return run_command(cmd)


def step7_esp32_validation(args):
    """Step 7: ESP32 hardware validation"""
    logger.info("=" * 60)
    logger.info("STEP 7: ESP32 Hardware Validation")
    logger.info("=" * 60)

    if not Path("dataset/esp32_hardware/metadata.csv").exists():
        logger.warning("ESP32 hardware dataset not available, skipping")
        return True

    cmd = [
        sys.executable, "scripts/training/evaluate.py",
        "--model", args.output,
        "--test-data", "dataset/esp32_hardware/metadata.csv",
        "--batch-size", str(args.batch_size),
        "--device", args.device,
        "--output", f"{args.output}_esp32.json"
    ]

    return run_command(cmd)


def main():
    parser = argparse.ArgumentParser(description="Complete palm vein training pipeline")
    parser.add_argument('--backbone', type=str, default='resnet50')
    parser.add_argument('--embedding-dim', type=int, default=512)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--lr', type=float, default=1e-4)
    parser.add_argument('--loss', type=str, default='triplet', choices=['triplet', 'arcface', 'cosface'])
    parser.add_argument('--margin', type=float, default=0.3)
    parser.add_argument('--output', type=str, default='model/palm_model_v1.pt')
    parser.add_argument('--device', type=str, default='cuda' if __import__('torch').cuda.is_available() else 'cpu')
    parser.add_argument('--pretrained', action='store_true', default=True)
    parser.add_argument('--no-pretrained', dest='pretrained', action='store_false')
    parser.add_argument('--skip-steps', type=str, default='', help='Comma-separated steps to skip (1-7)')

    args = parser.parse_args()

    skip_steps = set(args.skip_steps.split(',')) if args.skip_steps else set()

    steps = [
        (1, "Standardize Datasets", step1_standardize_datasets),
        (2, "Create Splits", step2_create_splits),
        (3, "Train Model", step3_train_model),
        (4, "Evaluate Model", step4_evaluate_model),
        (5, "Cross-Session Evaluation", step5_cross_session_eval),
        (6, "Cross-Dataset Evaluation", step6_cross_dataset_eval),
        (7, "ESP32 Validation", step7_esp32_validation),
    ]

    logger.info("Starting Palm Vein Training Pipeline")
    logger.info(f"Configuration: backbone={args.backbone}, dim={args.embedding_dim}, loss={args.loss}")

    for step_num, step_name, step_func in steps:
        if str(step_num) in skip_steps:
            logger.info(f"Skipping Step {step_num}: {step_name}")
            continue

        logger.info(f"\n>>> Step {step_num}: {step_name}")
        success = step_func(args)

        if not success:
            logger.error(f"Step {step_num} failed! Pipeline stopped.")
            sys.exit(1)

    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"Model saved to: {args.output}")
    logger.info(f"Results saved to: {args.output}_*.json")


if __name__ == "__main__":
    main()