#!/usr/bin/env python3
"""
Install and setup KittenTTS with proper model downloading using Hugging Face
"""

import os
import sys
import subprocess
from pathlib import Path

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub", "kittentts"])

def download_model_with_hf():
    """Download KittenTTS model using huggingface_hub"""
    print("\n" + "="*60)
    print("Downloading KittenTTS Model")
    print("="*60)
    
    try:
        from huggingface_hub import hf_hub_download, snapshot_download
        
        # Try to download the entire model repository
        print("\nDownloading model from Hugging Face...")
        
        try:
            # Download the entire repository
            local_dir = Path.home() / ".cache" / "kittentts" / "models"
            local_dir.mkdir(parents=True, exist_ok=True)
            
            # This will download all files from the repository
            downloaded_path = snapshot_download(
                repo_id="KittenML/kitten-tts-nano-0.1",
                local_dir=str(local_dir / "kitten-tts-nano-0.1"),
                local_dir_use_symlinks=False,
                ignore_patterns=["*.md", "*.txt", ".git*"]
            )
            
            print(f"✓ Model downloaded to: {downloaded_path}")
            
            # Set environment variable for KittenTTS to find the model
            os.environ["KITTENTTS_MODEL_PATH"] = downloaded_path
            
            return downloaded_path
            
        except Exception as e:
            print(f"Snapshot download failed: {e}")
            
            # Try downloading individual files
            print("\nTrying to download individual model files...")
            
            model_dir = Path.home() / ".cache" / "kittentts" / "models" / "kitten-tts-nano-0.1"
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # List of potential model files
            files_to_try = [
                "model.onnx",
                "model.safetensors",
                "pytorch_model.bin",
                "config.json",
                "tokenizer.json",
                "tokenizer_config.json",
                "special_tokens_map.json",
                "vocab.json",
                "merges.txt"
            ]
            
            downloaded_files = []
            for filename in files_to_try:
                try:
                    print(f"  Trying to download {filename}...")
                    file_path = hf_hub_download(
                        repo_id="KittenML/kitten-tts-nano-0.1",
                        filename=filename,
                        cache_dir=str(Path.home() / ".cache" / "huggingface"),
                        local_dir=str(model_dir),
                        local_dir_use_symlinks=False
                    )
                    downloaded_files.append(filename)
                    print(f"    ✓ Downloaded: {filename}")
                except Exception as e:
                    print(f"    ✗ Not found: {filename}")
            
            if downloaded_files:
                print(f"\n✓ Downloaded {len(downloaded_files)} files to: {model_dir}")
                os.environ["KITTENTTS_MODEL_PATH"] = str(model_dir)
                return str(model_dir)
            else:
                print("\n✗ No model files could be downloaded")
                return None
                
    except ImportError:
        print("✗ huggingface_hub not installed")
        subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub"])
        return download_model_with_hf()  # Retry after installation
    except Exception as e:
        print(f"✗ Error downloading model: {e}")
        return None

def test_kittentts_with_path(model_path=None):
    """Test KittenTTS with the downloaded model"""
    print("\n" + "="*60)
    print("Testing KittenTTS")
    print("="*60)
    
    try:
        from kittentts import KittenTTS
        
        # Try different initialization approaches
        approaches = []
        
        if model_path:
            approaches.extend([
                (model_path, "Downloaded path"),
                (str(Path(model_path) / "model.onnx"), "ONNX file path"),
            ])
        
        approaches.extend([
            ("KittenML/kitten-tts-nano-0.1", "Hugging Face ID"),
            ("kitten-tts-nano-0.1", "Short name"),
            (None, "Default"),
        ])
        
        model = None
        for path, description in approaches:
            try:
                print(f"\nTrying: {description}")
                if path:
                    model = KittenTTS(path)
                else:
                    model = KittenTTS()
                print(f"✓ Success with: {description}")
                break
            except Exception as e:
                print(f"✗ Failed: {str(e)[:100]}")
                continue
        
        if model:
            print("\nTesting audio generation...")
            audio = model.generate("Hello, testing KittenTTS.", voice="expr-voice-2-f")
            if audio is not None and len(audio) > 0:
                print(f"✓ Audio generated: {len(audio)} samples")
                print(f"  Shape: {audio.shape}")
                print(f"  Dtype: {audio.dtype}")
                return True
            else:
                print("✗ No audio generated")
                return False
        else:
            print("\n✗ Could not initialize KittenTTS with any method")
            return False
            
    except ImportError:
        print("✗ KittenTTS not installed")
        return False
    except Exception as e:
        print(f"✗ Error testing KittenTTS: {e}")
        return False

def main():
    """Main setup function"""
    
    # Install dependencies
    install_dependencies()
    
    # Download model
    model_path = download_model_with_hf()
    
    # Test KittenTTS
    success = test_kittentts_with_path(model_path)
    
    if success:
        print("\n" + "="*60)
        print("✅ SUCCESS! KittenTTS is working!")
        print("="*60)
        print("\nYou can now run the voice agent:")
        print("  1. Start Ollama: ollama serve")
        print("  2. Start agent: cd .. && ./start.sh")
        
        # Save the model path for future use
        if model_path:
            config_file = Path.home() / ".kittentts_config"
            with open(config_file, "w") as f:
                f.write(f"MODEL_PATH={model_path}\n")
            print(f"\nModel path saved to: {config_file}")
    else:
        print("\n" + "="*60)
        print("⚠️  Setup completed but testing failed")
        print("="*60)
        print("\nThe model may still work. Try running the agent anyway:")
        print("  cd .. && ./start.sh")
        print("\nIf it fails, you may need to install KittenTTS from source:")
        print("  git clone https://github.com/KittenML/KittenTTS")
        print("  cd KittenTTS && pip install -e .")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
