#!/usr/bin/env python
"""Convert trained model for backend deployment"""
import sys
import argparse
from pathlib import Path

import torch

sys.path.append(str(Path(__file__).parent.parent.parent))

from scripts.training.train import PalmVeinEncoder


def main():
    parser = argparse.ArgumentParser(description="Convert model for backend deployment")
    parser.add_argument('--checkpoint', type=str, required=True, help='Training checkpoint')
    parser.add_argument('--output', type=str, required=True, help='Output model path')
    parser.add_argument('--format', type=str, default='pytorch', choices=['pytorch', 'onnx', 'torchscript'])
    parser.add_argument('--embedding-dim', type=int, default=512)
    parser.add_argument('--backbone', type=str, default='resnet50')
    args = parser.parse_args()

    device = torch.device('cpu')  # Convert on CPU

    # Load checkpoint
    checkpoint = torch.load(args.checkpoint, map_location=device)

    # Create model
    model = PalmVeinEncoder(
        backbone=args.backbone,
        embedding_dim=args.embedding_dim,
        pretrained=False
    )
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    # Create output directory
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    if args.format == 'pytorch':
        # Save just the model state dict
        torch.save(model.state_dict(), args.output)
        print(f"Saved PyTorch state dict to {args.output}")

    elif args.format == 'torchscript':
        # Trace and save as TorchScript
        example_input = torch.randn(1, 3, 224, 224)
        traced = torch.jit.trace(model, example_input)
        traced.save(args.output)
        print(f"Saved TorchScript model to {args.output}")

    elif args.format == 'onnx':
        # Export to ONNX
        example_input = torch.randn(1, 3, 224, 224)
        torch.onnx.export(
            model,
            example_input,
            args.output,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['embedding'],
            dynamic_axes={'input': {0: 'batch_size'}, 'embedding': {0: 'batch_size'}}
        )
        print(f"Saved ONNX model to {args.output}")

    # Also save model config
    config_path = Path(args.output).with_suffix('.json')
    import json
    config = {
        'model_version': 'palm_model_v1',
        'backbone': args.backbone,
        'embedding_dim': args.embedding_dim,
        'input_size': [3, 224, 224],
        'normalization': {
            'mean': [0.485, 0.456, 0.406],
            'std': [0.229, 0.224, 0.225]
        },
        'training_epoch': checkpoint.get('epoch', 'unknown'),
        'training_loss': args.loss if hasattr(args, 'loss') else 'unknown'
    }
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Saved model config to {config_path}")


if __name__ == "__main__":
    main()