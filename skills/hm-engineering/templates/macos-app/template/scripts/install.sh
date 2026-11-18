#!/bin/bash
# Builds, bundles, signs and installs "__APP_NAME__" into ~/Applications, then proves it stays alive.
# Ends with "installed and alive" or exits non-zero.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="__APP_NAME__"
EXE="__TARGET__"
BUNDLE_ID="__BUNDLE_ID__"
APP="$HOME/Applications/$NAME.app"
ALIVE_SECONDS="${ALIVE_SECONDS:-6}"

cd "$ROOT"
swift build -c release
BIN="$(swift build -c release --show-bin-path)/$EXE"

STAGE="$ROOT/.build/stage/$NAME.app"
rm -rf "${STAGE:?}"
mkdir -p "$STAGE/Contents/MacOS" "$STAGE/Contents/Resources"
cp "$BIN" "$STAGE/Contents/MacOS/$EXE"
ICON_KEY=""
if [ -f "$ROOT/Resources/AppIcon.icns" ]; then  # optional: drop an AppIcon.icns in Resources/
  cp "$ROOT/Resources/AppIcon.icns" "$STAGE/Contents/Resources/AppIcon.icns"
  ICON_KEY="<key>CFBundleIconFile</key><string>AppIcon</string>"
fi
cat > "$STAGE/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
  <key>CFBundleName</key><string>$NAME</string>
  <key>CFBundleDisplayName</key><string>$NAME</string>
  <key>CFBundleExecutable</key><string>$EXE</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>26.0</string>
  <key>NSHighResolutionCapable</key><true/>
  $ICON_KEY
</dict></plist>
PLIST

# Signing: a stable "Apple Development" identity keeps privacy permissions (TCC) across rebuilds.
# Without one, ad-hoc signing works but macOS asks for those permissions again after every build.
IDENTITY="$(security find-identity -v -p codesigning 2>/dev/null | awk -F'"' '/Apple Development/ {print $2; exit}')"
if [ -n "$IDENTITY" ]; then
  codesign --force --deep --sign "$IDENTITY" "$STAGE" >/dev/null
  echo "signed with: $IDENTITY"
else
  codesign --force --deep --sign - "$STAGE" >/dev/null
  echo "WARNING: no 'Apple Development' identity found; signed ad-hoc." >&2
  echo "WARNING: privacy permissions (microphone, accessibility, screen) will be requested again after every build." >&2
fi

# Replace the installed copy (only this app's bundle path) and launch it.
pkill -f "$APP/Contents/MacOS/$EXE" 2>/dev/null || true
mkdir -p "$HOME/Applications"
rm -rf "${APP:?}"
cp -R "$STAGE" "$APP"
open "$APP"

# Liveness: the app must still be running after ALIVE_SECONDS.
sleep "$ALIVE_SECONDS"
if pgrep -f "$APP/Contents/MacOS/$EXE" >/dev/null; then
  echo "installed and alive: $APP"
else
  echo "FAILED: $NAME exited within ${ALIVE_SECONDS}s of launch" >&2
  exit 1
fi
