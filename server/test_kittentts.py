#!/usr/bin/env python3
"""
Test script to verify KittenTTS installation and audio playback
"""

import sys
import numpy as np

def test_kittentts():
    """Test KittenTTS installation and basic functionality"""
    print("Testing KittenTTS installation...")
    
    try:
        from kittentts import KittenTTS
        print("✓ KittenTTS imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import KittenTTS: {e}")
        print("\nPlease install KittenTTS with: pip install kittentts")
        return False
    
    try:
        print("\nInitializing KittenTTS model...")
        model = KittenTTS("KittenML/kitten-tts-nano-0.1")
        print("✓ Model initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize model: {e}")
        return False
    
    try:
        print("\nGenerating test audio...")
        text = "Hello, this is a test of KittenTTS. If you can hear this, the system is working correctly."
        voice = "expr-voice-2-f"
        
        audio = model.generate(text, voice=voice)
        print(f"✓ Audio generated successfully")
        print(f"  Audio shape: {audio.shape}")
        print(f"  Audio dtype: {audio.dtype}")
        print(f"  Audio range: [{audio.min():.3f}, {audio.max():.3f}]")
        
        # Test audio conversion
        audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        print(f"✓ Audio converted to int16 successfully")
        print(f"  Bytes size: {len(audio_int16.tobytes())} bytes")
        
    except Exception as e:
        print(f"✗ Failed to generate audio: {e}")
        return False
    
    print("\n✓ All tests passed! KittenTTS is working correctly.")
    return True

def test_sounddevice_playback():
    """Optional: Test audio playback with sounddevice"""
    try:
        import sounddevice as sd
        from kittentts import KittenTTS
        
        print("\nTesting audio playback...")
        model = KittenTTS("KittenML/kitten-tts-nano-0.1")
        audio = model.generate("Testing audio playback.", voice="expr-voice-2-f")
        
        print("Playing audio... (requires sounddevice)")
        sd.play(audio, samplerate=24000)
        sd.wait()
        print("✓ Audio playback completed")
        
    except ImportError:
        print("\nNote: sounddevice not installed. To test audio playback, install with:")
        print("  pip install sounddevice")
    except Exception as e:
        print(f"\nCouldn't test audio playback: {e}")

if __name__ == "__main__":
    success = test_kittentts()
    if success:
        test_sounddevice_playback()
    sys.exit(0 if success else 1)
