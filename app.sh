#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# app.sh — Avvia l'applicazione Investitore Intelligente (Flask)
#
# Uso:
#   ./app.sh          # avvio normale
#   ./app.sh --help   # mostra questo messaggio
# -----------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
APP_ENTRY="$SCRIPT_DIR/app.py"
ENV_FILE="$SCRIPT_DIR/.env"

# ── Help ────────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Uso: ./app.sh [--help]"
  echo ""
  echo "  Attiva il virtualenv (.venv), carica le variabili da .env (se presente)"
  echo "  e avvia l'applicazione Flask (app.py) sulla porta 5001."
  exit 0
fi

# ── Controllo virtualenv ─────────────────────────────────────────────────────
if [[ ! -f "$VENV_DIR/bin/python" ]]; then
  echo "[ERRORE] Virtualenv non trovato in '$VENV_DIR'."
  echo "         Esegui prima: uv sync"
  exit 1
fi

# ── Attiva virtualenv ────────────────────────────────────────────────────────
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# ── Carica .env (opzionale) ──────────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
  echo "[INFO] Caricamento variabili da .env"
  set -o allexport
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +o allexport
fi

# ── Crea directory necessarie ────────────────────────────────────────────────
mkdir -p "$SCRIPT_DIR/data"
mkdir -p "$SCRIPT_DIR/logs"

# ── Avvio ────────────────────────────────────────────────────────────────────
echo "[INFO] Avvio Investitore Intelligente su http://localhost:5001"
exec python "$APP_ENTRY"
