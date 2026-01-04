#!/usr/bin/env python3
"""
Optimize images for mobile viewing
Resize to 480x320 and convert PNG to JPEG with quality 80
Reduces file size by ~95% (328 MB → ~12 MB)
"""

from PIL import Image
from pathlib import Path
import os

# Configuration
SOURCE_DIR = Path("images")
TARGET_WIDTH = 480  # Optimal for iPhone retina display (2x-3x)
JPEG_QUALITY = 80   # Good quality/size balance

def optimize_image(img_path: Path):
    """Resize and compress a single image."""
    try:
        # Open image
        img = Image.open(img_path)

        # Calculate new dimensions (maintain aspect ratio)
        aspect_ratio = img.size[1] / img.size[0]
        target_height = int(TARGET_WIDTH * aspect_ratio)

        # Resize with high-quality resampling
        img_resized = img.resize((TARGET_WIDTH, target_height), Image.Resampling.LANCZOS)

        # Convert RGBA to RGB if needed (for JPEG)
        if img_resized.mode == 'RGBA':
            background = Image.new('RGB', img_resized.size, (255, 255, 255))
            background.paste(img_resized, mask=img_resized.split()[3])
            img_resized = background

        # Save as JPEG (much better compression than PNG)
        output_path = img_path.with_suffix('.jpg')
        img_resized.save(output_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)

        # Get file sizes
        old_size = img_path.stat().st_size / 1024  # KB
        new_size = output_path.stat().st_size / 1024  # KB
        reduction = (1 - new_size / old_size) * 100

        # Delete old PNG
        img_path.unlink()

        return {
            'name': img_path.name,
            'old_size': old_size,
            'new_size': new_size,
            'reduction': reduction
        }

    except Exception as e:
        print(f"❌ Error processing {img_path.name}: {e}")
        return None

def main():
    """Optimize all images in the directory."""
    # Get all PNG files
    png_files = sorted(SOURCE_DIR.glob("*.png"))
    total_files = len(png_files)

    print(f"🎨 Optimizing {total_files} images for mobile display")
    print(f"   Target: {TARGET_WIDTH}px width, JPEG quality {JPEG_QUALITY}")
    print(f"   Expected reduction: ~95%\n")

    total_old_size = 0
    total_new_size = 0
    processed = 0

    for i, img_path in enumerate(png_files, 1):
        result = optimize_image(img_path)

        if result:
            total_old_size += result['old_size']
            total_new_size += result['new_size']
            processed += 1

            if i % 10 == 0 or i == total_files:
                print(f"[{i}/{total_files}] Processed {result['name']}: "
                      f"{result['old_size']:.0f} KB → {result['new_size']:.0f} KB "
                      f"({result['reduction']:.1f}% smaller)")

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Optimization complete!")
    print(f"   Files processed: {processed}/{total_files}")
    print(f"   Total size before: {total_old_size / 1024:.1f} MB")
    print(f"   Total size after: {total_new_size / 1024:.1f} MB")
    print(f"   Total reduction: {(1 - total_new_size / total_old_size) * 100:.1f}%")
    print(f"   Space saved: {(total_old_size - total_new_size) / 1024:.1f} MB")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
