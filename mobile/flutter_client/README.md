# Flutter WebRTC Client

This Flutter application mirrors the Pipecat `smallwebrtc` transport used by the web client.
It captures microphone audio, posts offers to the running Pipecat server, and plays the
remote audio stream returned by the `/api/offer` endpoint.

## Prerequisites

- Flutter SDK 3.3.0 or newer
- An Android device/emulator (the project only targets Android)
- The Pipecat server from this repository running locally on port `7860`

## Running the client

```bash
cd mobile/flutter_client
flutter pub get
flutter run
```

When the app launches:

1. Ensure the **Offer endpoint** text field contains the correct base URL.
   - Android emulator: `http://10.0.2.2:7860/api/offer`
   - Physical device: replace with your host machine's LAN IP, e.g. `http://192.168.1.50:7860/api/offer`
2. Grant the microphone permission when prompted.
3. Tap **Connect to /api/offer** to start streaming audio in both directions.
4. Use **Disconnect** to close the peer connection and release audio resources.

The client automatically logs structured JSON events to help diagnose signaling or media
issues. Remote audio is forced to play through the speakerphone for easier monitoring.
