#!/usr/bin/env bash
set -euo pipefail

# ====== CONFIG (troque só aqui) ======
URL="https://www.instagram.com/reel/DMGp0w-MCya/?igsh=bmU5M3V2c2c2YWNq"
TITLE="Reels DQFQsquAclZ"
TESSERACT="/d/Usuarios/08853011106/AppData/Local/Programs/Tesseract-OCR/tesseract.exe"

# Opção A (recomendado): exportar antes de rodar
# export GEMINI_API_KEY="SUA_CHAVE"
# Opção B: colocar aqui (não recomendado pra segurança)
GEMINI_API_KEY="${GEMINI_API_KEY:-}"

OUT_JSON="results/analysis.json"
# =====================================

cd "$(dirname "$0")"

# 1) Ativar venv
source .venv/Scripts/activate

# 2) Garantir pastas
mkdir -p results downloads

# 3) Checar API key
if [[ -z "$GEMINI_API_KEY" ]]; then
  echo "ERRO: GEMINI_API_KEY não definida."
  echo 'No Git Bash: export GEMINI_API_KEY="SUA_CHAVE"'
  exit 1
fi

# 4) Rodar pipeline (download + frames + OCR + Gemini)
python -m reel_analyzer.cli \
  --url "$URL" \
  --i-own-this \
  --gemini-api-key "$GEMINI_API_KEY" \
  --tesseract-cmd "$TESSERACT" \
  --ocr-langs "por+eng" \
  --vision \
  --out "$OUT_JSON"

# 5) Print rápido no terminal
python - <<'PY'
import json
p="results/analysis.json"
d=json.load(open(p,"r",encoding="utf-8"))
print("\n=== GEMINI (raw) ===\n")
print(d.get("gemini",{}).get("text_analysis",{}).get("raw","(sem campo raw)"))
print("\n=== OCR (primeiros 800) ===\n")
print((d.get("ocr",{}).get("consolidated_text","") or "")[:800])
PY

# 6) Exportar pro Google Docs
python export_to_gdocs.py "$OUT_JSON" --title "$TITLE"

echo ""
echo "✅ Fluxo completo finalizado."
