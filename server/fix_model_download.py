#!/usr/bin/env python3
"""
Direct fix for KittenTTS model download issue
"""

import os
import sys
import json
from pathlib import Path
import urllib.request
import tarfile
import zipfile

def download_file(url, dest_path):
    """Download a file with progress indicator"""
    print(f"Downloading from: {url}")
    print(f"Saving to: {dest_path}")
    
    try:
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(dest_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"Progress: {percent:.1f}%", end='\r')
            
            print(f"\n✓ Downloaded: {dest_path}")
            return True
    except Exception as e:
        print(f"✗ Download failed: {e}")
        return False

def setup_kittentts_manual():
    """Manually download and setup KittenTTS model files"""
    
    print("=" * 60)
    print("KittenTTS Manual Model Setup")
    print("=" * 60)
    
    # Create cache directories
    cache_base = Path.home() / ".cache" / "kittentts"
    model_dir = cache_base / "KittenML" / "kitten-tts-nano-0.1"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nModel directory: {model_dir}")
    
    # Model files we need to download
    model_files = {
        "model.onnx": "https://huggingface.co/KittenML/kitten-tts-nano-0.1/resolve/main/model.onnx",
        "config.json": "https://huggingface.co/KittenML/kitten-tts-nano-0.1/resolve/main/config.json",
        "tokenizer.json": "https://huggingface.co/KittenML/kitten-tts-nano-0.1/resolve/main/tokenizer.json",
    }
    
    # Download each file
    print("\nDownloading model files...")
    for filename, url in model_files.items():
        dest_path = model_dir / filename
        if dest_path.exists():
            print(f"✓ {filename} already exists")
        else:
            print(f"\nDownloading {filename}...")
            if not download_file(url, dest_path):
                return False
    
    # Create a symlink in the default location KittenTTS might expect
    default_paths = [
        Path.home() / ".cache" / "huggingface" / "hub",
        Path.home() / ".kittentts",
        Path.cwd() / "KittenML",
    ]
    
    for path in default_paths:
        path.mkdir(parents=True, exist_ok=True)
        link_path = path / "kitten-tts-nano-0.1"
        if not link_path.exists():
            try:
                link_path.symlink_to(model_dir)
                print(f"✓ Created symlink: {link_path}")
            except:
                pass
    
    print("\n✓ Model files downloaded successfully!")
    return True

def fix_kittentts_import():
    """Try to fix KittenTTS to use the downloaded model"""
    
    print("\nTesting KittenTTS with downloaded model...")
    
    try:
        # Set environment variable to point to model location
        os.environ["KITTENTTS_CACHE_DIR"] = str(Path.home() / ".cache" / "kittentts")
        
        # Try importing and initializing
        from kittentts import KittenTTS
        
        # Try different initialization methods
        model_paths = [
            "KittenML/kitten-tts-nano-0.1",
            str(Path.home() / ".cache" / "kittentts" / "KittenML" / "kitten-tts-nano-0.1"),
            str(Path.home() / ".cache" / "kittentts" / "KittenML" / "kitten-tts-nano-0.1" / "model.onnx"),
        ]
        
        model = None
        for path in model_paths:
            try:
                print(f"Trying to load from: {path}")
                model = KittenTTS(path)
                print(f"✓ Successfully loaded model from: {path}")
                break
            except Exception as e:
                print(f"  Failed: {e}")
                continue
        
        if model is None:
            print("\n✗ Could not initialize KittenTTS with any path")
            print("\nTrying alternative approach...")
            
            # Try to patch KittenTTS to use our model
            import kittentts
            if hasattr(kittentts, '__file__'):
                kittentts_path = Path(kittentts.__file__).parent
                print(f"KittenTTS installed at: {kittentts_path}")
                
                # Create models directory in KittenTTS installation
                models_dir = kittentts_path / "models"
                models_dir.mkdir(exist_ok=True)
                
                # Copy model files there
                import shutil
                model_src = Path.home() / ".cache" / "kittentts" / "KittenML" / "kitten-tts-nano-0.1"
                model_dst = models_dir / "kitten-tts-nano-0.1"
                
                if not model_dst.exists():
                    shutil.copytree(model_src, model_dst)
                    print(f"✓ Copied model to: {model_dst}")
                
                # Try loading again
                model = KittenTTS("kitten-tts-nano-0.1")
                print("✓ Model loaded after copying to package directory!")
        
        # Test generation
        if model:
            print("\nTesting audio generation...")
            audio = model.generate("Hello world", voice="expr-voice-2-f")
            if audio is not None and len(audio) > 0:
                print(f"✓ Audio generated: {len(audio)} samples")
                return True
            else:
                print("✗ No audio generated")
                return False
        
    except ImportError:
        print("✗ KittenTTS not installed")
        print("Run: pip install kittentts")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return False

def main():
    """Main setup function"""
    
    # First, ensure KittenTTS is installed
    try:
        import kittentts
        print("✓ KittenTTS package is installed")
    except ImportError:
        print("Installing KittenTTS...")
        os.system("pip install kittentts")
    
    # Download model files
    if not setup_kittentts_manual():
        print("\n❌ Failed to download model files")
        return False
    
    # Test the setup
    if not fix_kittentts_import():
        print("\n⚠️  Model downloaded but initialization failed")
        print("\nTry running the server anyway - it may work!")
        return False
    
    print("\n" + "=" * 60)
    print("✅ KittenTTS is fully configured and working!")
    print("=" * 60)
    print("\nYou can now run the voice agent:")
    print("  1. Start Ollama: ollama serve")
    print("  2. Start agent: ./start.sh")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
