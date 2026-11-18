#!/usr/bin/env python3
"""Single source for privacy permissions: permissions.json -> Info.plist keys AND signing entitlements.

With hardened runtime, a permission request whose entitlement is missing from the signature is denied
with no prompt and no error. Generating both sides from one file makes that mismatch impossible, and
`verify` proves it on the signed app.

    python3 tools/permissions.py plist-keys                 # <key>/<string> lines for Info.plist
    python3 tools/permissions.py entitlements OUT.plist     # entitlements file for codesign
    python3 tools/permissions.py verify PATH.app            # signed app: every usage key has its entitlement
"""

from __future__ import annotations

import json
import plistlib
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "permissions.json"
USAGE_ENTITLEMENTS = {
    "NSMicrophoneUsageDescription": "com.apple.security.device.audio-input",
    "NSCameraUsageDescription": "com.apple.security.device.camera",
    "NSCalendarsUsageDescription": "com.apple.security.personal-information.calendars",
    "NSCalendarsFullAccessUsageDescription": "com.apple.security.personal-information.calendars",
    "NSCalendarsWriteOnlyAccessUsageDescription": "com.apple.security.personal-information.calendars",
    "NSRemindersUsageDescription": "com.apple.security.personal-information.calendars",
    "NSRemindersFullAccessUsageDescription": "com.apple.security.personal-information.calendars",
    "NSContactsUsageDescription": "com.apple.security.personal-information.addressbook",
    "NSLocationUsageDescription": "com.apple.security.personal-information.location",
    "NSLocationWhenInUseUsageDescription": "com.apple.security.personal-information.location",
    "NSLocationAlwaysAndWhenInUseUsageDescription": "com.apple.security.personal-information.location",
    "NSPhotoLibraryUsageDescription": "com.apple.security.personal-information.photos-library",
    "NSHealthShareUsageDescription": "com.apple.developer.healthkit",
    "NSHealthUpdateUsageDescription": "com.apple.developer.healthkit",
}


def load() -> dict[str, str]:
    data = json.loads(SOURCE.read_text(encoding="utf-8")) if SOURCE.exists() else {}
    if not isinstance(data, dict) or not all(isinstance(k, str) and k.endswith("UsageDescription") and isinstance(v, str) and v.strip() for k, v in data.items()):
        raise SystemExit("permissions.json: object of \"NS...UsageDescription\": \"non-empty text shown to the user\"")
    return data


def missing(usage_keys: list[str], entitlements: Mapping[str, object]) -> list[str]:
    return sorted(f"{k} needs {USAGE_ENTITLEMENTS[k]}" for k in usage_keys if k in USAGE_ENTITLEMENTS and entitlements.get(USAGE_ENTITLEMENTS[k]) is not True)


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else ""
    if command == "plist-keys":
        for key, text in load().items():
            print(f"  <key>{escape(key)}</key><string>{escape(text)}</string>")
        return 0
    if command == "entitlements" and len(argv) == 3:
        ents = {USAGE_ENTITLEMENTS[k]: True for k in load() if k in USAGE_ENTITLEMENTS}
        Path(argv[2]).write_bytes(plistlib.dumps(ents))
        return 0
    if command == "verify" and len(argv) == 3:
        app = Path(argv[2])
        usage = [k for k in plistlib.loads((app / "Contents" / "Info.plist").read_bytes()) if k.endswith("UsageDescription")]
        raw = subprocess.run(["codesign", "-d", "--entitlements", "-", "--xml", str(app)], capture_output=True, check=True).stdout
        start = raw.find(b"<?xml")
        ents = plistlib.loads(raw[start:]) if start >= 0 else {}
        info = subprocess.run(["codesign", "-dv", str(app)], capture_output=True, text=True, check=True).stderr
        flags = re.search(r"flags=0x[0-9a-f]+\(([^)]*)\)", info)
        if not flags or "runtime" not in flags.group(1).split(","):
            print("permissions: FAIL app is not signed with hardened runtime", file=sys.stderr)
            return 1
        problems = missing(usage, ents if isinstance(ents, dict) else {})
        if problems:
            print("permissions: FAIL request would be denied with no prompt: " + "; ".join(problems), file=sys.stderr)
            return 1
        print(f"permissions: OK ({len(usage)} usage description(s), entitlements match)")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
