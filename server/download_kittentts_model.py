#!/usr/bin/env python3
"""
Download and cache KittenTTS models
"""

import os
import sys
from pathlib import Path

def download_kittentts_models():
    """Download and cache KittenTTS models"""
    print("=" * 60)
    print("KittenTTS Model Downloader")
    print("=" * 60)
    
    # Check if KittenTTS is installed
    try:
        from kittentts import KittenTTS
        print("✓ KittenTTS is installed")
    except ImportError:
        print("✗ KittenTTS not installed")
        print("\nPlease run: pip install kittentts")
        return False
    
    # Try to download from Hugging Face
    try:
        from huggingface_hub import snapshot_download
        print("✓ huggingface_hub is installed")
        
        # Download the model files
        print("\nDownloading KittenTTS model from Hugging Face...")
        print("This may take a few minutes on first run...")
        
        cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = snapshot_download(
            repo_id="KittenML/kitten-tts-nano-0.1",
            cache_dir=str(cache_dir),
            local_dir_use_symlinks=False
        )
        print(f"✓ Model downloaded to: {model_path}")
        
    except ImportError:
        print("⚠ huggingface_hub not installed, installing now...")
        os.system("pip install huggingface_hub")
        
        # Try again after installation
        try:
            from huggingface_hub import snapshot_download
            
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            print("\nDownloading KittenTTS model from Hugging Face...")
            model_path = snapshot_download(
                repo_id="KittenML/kitten-tts-nano-0.1",
                cache_dir=str(cache_dir),
                local_dir_use_symlinks=False
            )
            print(f"✓ Model downloaded to: {model_path}")
        except Exception as e:
            print(f"✗ Failed to download via huggingface_hub: {e}")
    
    except Exception as e:
        print(f"✗ Error downloading model: {e}")
    
    # Now try to initialize KittenTTS with the model
    print("\nInitializing KittenTTS to verify model...")
    try:
        model = KittenTTS("KittenML/kitten-tts-nano-0.1")
        print("✓ KittenTTS model initialized successfully!")
        
        # Test generation
        print("\nTesting audio generation...")
        test_text = "Hello, this is a test."
        audio = model.generate(test_text, voice="expr-voice-2-f")
        
        if audio is not None and len(audio) > 0:
            print(f"✓ Audio generated successfully ({len(audio)} samples)")
            print(f"  Shape: {audio.shape}")
            print(f"  Dtype: {audio.dtype}")
            return True
        else:
            print("✗ No audio generated")
            return False
            
    except Exception as e:
        print(f"✗ Failed to initialize KittenTTS: {e}")
        print("\nTroubleshooting:")
        print("1. Check internet connection")
        print("2. Try clearing cache: rm -rf ~/.cache/kittentts")
        print("3. Reinstall: pip uninstall kittentts && pip install kittentts")
        return False

if __name__ == "__main__":
    print("This script will download and cache the KittenTTS model.\n")
    
    success = download_kittentts_models()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ SUCCESS! KittenTTS is ready to use.")
        print("=" * 60)
        print("\nYou can now run the voice agent:")
        print("  cd /Users/raymondgonzalez/Downloads/macos-local-voice-agents-main")
        print("  ./start.sh")
    else:
        print("\n" + "=" * 60)
        print("❌ Setup failed. Please check the errors above.")
        print("=" * 60)
    
    sys.exit(0 if success else 1)
