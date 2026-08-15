#!/usr/bin/env sh
# Build the pilot app pointed at the deployed backends.
#
# Use this rather than a bare `flutter build`. Without the dart-defines below,
# CertConfig falls back to its defaults — api.relationshipai.com and
# ws.relationshipai.com — which do not exist. The app builds and installs
# perfectly and then fails every request with a DNS error, which reads as a
# backend outage rather than a missing build flag.
#
#   ./build_pilot.sh apk      → android/app/build/outputs/flutter-apk/app-release.apk
#   ./build_pilot.sh ios      → an unsigned iOS build (needs Xcode to install)
#   ./build_pilot.sh run      → run on an attached device/emulator
set -e

TARGET="${1:-apk}"

DEFINES="--dart-define=API_HOST=bliss-django.onrender.com \
--dart-define=WS_HOST=bliss-fastapi.onrender.com \
--dart-define=API_SCHEME=https"

echo "Backends:"
echo "  Django   https://bliss-django.onrender.com"
echo "  FastAPI  https://bliss-fastapi.onrender.com"
echo

case "$TARGET" in
  apk)
    # shellcheck disable=SC2086
    flutter build apk --release $DEFINES
    echo
    echo "APK: build/app/outputs/flutter-apk/app-release.apk"
    echo "Send that file to the test couple's Android phones."
    ;;
  ios)
    # shellcheck disable=SC2086
    flutter build ios --release --no-codesign $DEFINES
    echo
    echo "Unsigned iOS build. Open ios/Runner.xcworkspace in Xcode to install"
    echo "on a device — TestFlight needs a paid Apple Developer account."
    ;;
  run)
    # shellcheck disable=SC2086
    flutter run --release $DEFINES
    ;;
  *)
    echo "usage: $0 [apk|ios|run]" >&2
    exit 2
    ;;
esac
