#!/usr/bin/env python
"""
Organize Tongji flat files into subject folders.
Assumes sequential numbering: 00001-06000 = 300 subjects × 20 images each.
"""
import os
import shutil
from pathlib import Path
import argparse

def organize_tongji(raw_dir: str, images_per_subject: int = 20):
    """
    Organize flat TIFF files into subject folders.
    
    Expected input: 00001.tiff, 00002.tiff, ..., 06000.tiff
    Output: 001/001_01.tiff, 001/001_02.tiff, ..., 300/300_20.tiff
    """
    raw_path = Path(raw_dir)
    
    # Process session 1 (root level files)
    session1_files = sorted([f for f in raw_path.glob("*.tiff") if f.is_file()])
    print(f"Session 1: {len(session1_files)} files")
    
    # Process session 2 (subfolder)
    session2_path = raw_path / "session2"
    session2_files = sorted([f for f in session2_path.glob("*.tiff") if f.is_file()])
    print(f"Session 2: {len(session2_files)} files")
    
    if len(session1_files) != len(session2_files):
        print(f"WARNING: Session counts differ: {len(session1_files)} vs {len(session2_files)}")
    
    num_subjects = len(session1_files) // images_per_subject
    print(f"Organizing into {num_subjects} subjects × {images_per_subject} images")
    
    for session_name, files in [("session1", session1_files), ("session2", session2_files)]:
        for subject_idx in range(num_subjects):
            subject_num = subject_idx + 1
            subject_dir = raw_path / f"{subject_num:03d}"
            subject_dir.mkdir(exist_ok=True)
            
            start_idx = subject_idx * images_per_subject
            end_idx = start_idx + images_per_subject
            
            for img_idx, file_path in enumerate(files[start_idx:end_idx]):
                new_name = f"{subject_num:03d}_{img_idx+1:02d}.tiff"
                dest = subject_dir / new_name
                shutil.move(str(file_path), str(dest))
            
            if subject_idx % 50 == 0:
                print(f"  {session_name}: Organized subject {subject_num:03d}")
    
    # Remove empty session2 folder
    if session2_path.exists() and not any(session2_path.iterdir()):
        session2_path.rmdir()
        print("Removed empty session2 folder")
    
    print("Organization complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default="dataset/tongji/raw")
    parser.add_argument("--images-per-subject", type=int, default=20)
    args = parser.parse_args()
    
    organize_tongji(args.raw_dir, args.images_per_subject)