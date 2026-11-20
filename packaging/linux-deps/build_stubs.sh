#!/usr/bin/env bash
# Developer helper for Linux/CI only -- NOT part of the Windows product.
#
# Qt's "offscreen" platform needs a handful of system libraries (libGL,
# libEGL, libxkbcommon, libdbus-1, libfontconfig) that bare containers often
# lack.  This script compiles tiny no-op stand-ins so that GUI smoke tests
# (screenshot generation, widget tests) can run headless.
#
# Usage:
#   bash packaging/linux-deps/build_stubs.sh /tmp/qtstubs
#   LD_LIBRARY_PATH=/tmp/qtstubs QT_QPA_PLATFORM=offscreen python -m pytest
set -euo pipefail

OUT="${1:-/tmp/qtstubs}"
SRC="$(cd "$(dirname "$0")" && pwd)/src"
mkdir -p "$OUT"

cc -shared -fPIC -O2 -Wl,-soname,libxkbcommon.so.0 \
   -Wl,--version-script="$SRC/xkb_ver.map" \
   -o "$OUT/libxkbcommon.so.0" "$SRC/libxkbcommon.c"

cc -shared -fPIC -O2 -Wl,-soname,libdbus-1.so.3 \
   -Wl,--version-script="$SRC/dbus_ver.map" \
   -o "$OUT/libdbus-1.so.3" \
   "$SRC/libdbus-1.c" "$SRC/dbus_extra.c" "$SRC/dbus_fill.c"

# fontconfig shim: reads font paths from $SMARTSCAN_FC_FONTS (colon separated)
cc -shared -fPIC -O2 -Wl,-soname,libfontconfig.so.1 \
   -o "$OUT/libfontconfig.so.1" "$SRC/libfontconfig.c"

cc -shared -fPIC -O2 -Wl,-soname,libEGL.so.1 \
   -o "$OUT/libEGL.so.1" "$SRC/egl_extra.c" "$SRC/egl_fill.c"

cc -shared -fPIC -O2 -Wl,-soname,libGL.so.1 \
   -o "$OUT/libGL.so.1" "$SRC/gl_extra.c"

# libxkbcommon-x11 and libGLESv2 are optional for the offscreen platform.
cat > "$OUT/libxkbcommon-x11.so.0.c" <<'C'
void *stub_noop(void *arg) { (void)arg; return 0; }
C
cc -shared -fPIC -o "$OUT/libxkbcommon-x11.so.0" "$OUT/libxkbcommon-x11.so.0.c"

echo "Built headless Qt stubs in $OUT (test-only)."
