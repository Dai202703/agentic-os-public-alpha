#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON:-python3}
INSTALL_DIR=${AOS_INSTALL_DIR:-"$HOME/.local/bin"}
INSTALL_LAUNCHER=${AOS_INSTALL_LAUNCHER:-"$ROOT_DIR/bin/aos"}
SKIP_CHECKS=${AOS_INSTALL_SKIP_CHECKS:-0}

PYTHONPATH_VALUE="$ROOT_DIR/src"
if [ "${PYTHONPATH:-}" ]; then
  PYTHONPATH_VALUE="$PYTHONPATH_VALUE:$PYTHONPATH"
fi

if [ "$SKIP_CHECKS" != "1" ]; then
  echo "Running AOS pre-install checks..."
  env PYTHONPATH="$PYTHONPATH_VALUE" "$PYTHON_BIN" -m unittest discover -s tests -v
  "$ROOT_DIR/scripts/readiness_smoke.py" --launcher "$INSTALL_LAUNCHER" --json
fi

"$PYTHON_BIN" "$ROOT_DIR/scripts/manage_global_aos.py" install \
  --launcher "$INSTALL_LAUNCHER" \
  --install-dir "$INSTALL_DIR"

if [ "$SKIP_CHECKS" != "1" ]; then
  CLEAN_CHECK_HOME=0
  if [ "${AOS_INSTALL_CHECK_HOME:-}" ]; then
    CHECK_HOME=$AOS_INSTALL_CHECK_HOME
  else
    CHECK_HOME=$(mktemp -d "${TMPDIR:-/tmp}/aos-install-check.XXXXXX")
    CLEAN_CHECK_HOME=1
  fi

  "$INSTALL_DIR/aos" --os-home "$CHECK_HOME" init
  "$INSTALL_DIR/aos" --os-home "$CHECK_HOME" doctor --summary

  if [ "$CLEAN_CHECK_HOME" = "1" ]; then
    rm -rf "$CHECK_HOME"
  fi
fi

"$INSTALL_DIR/aos" version

case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "Note: $INSTALL_DIR is not on PATH. Add it to your shell profile to run 'aos' directly."
    ;;
esac

echo "aos install complete: $INSTALL_DIR/aos"
