#!/usr/bin/env bash
set -euo pipefail

# Uso:
#   export GEMINI_API_KEY="SUA_CHAVE_AQUI"
#   ./run_reel.sh "URL_DO_REEL" "Título opcional pro Google Docs"
#
# Exemplo:
#   ./run_reel.sh "https://www.instagram.com/reel/DQFQsquAclZ/?igsh=ejgzbjYxYzdkMm8x" "Reels DRfrm82E5fI"

URL="${1:?Passe a URL do Reels como primeiro parâmetro}"
TITLE="${2:-Reels analisado}"

# Caminho do Tesseract no seu Windows (via Git Bash)
TESS="/d/Usuarios/08853011106/AppData/Local/Programs/Tesseract-OCR/tesseract.exe"

# Vai pra pasta onde está este script
cd "$(dirname "$0")"

# Garante venv ativo
if [ ! -d ".venv" ]; then
  echo "[run_reel] Criando venv .venv (Python 3.13)..."
  py -3.13 -m venv .venv
fi

# Ativa venv (Git Bash no Windows)
source .venv/Scripts/activate

# Garante dependências instaladas (editável)
python -m pip install -U pip >/dev/null
pip install -e . >/dev/null

# Checa API key
: "${GEMINI_API_KEY:?Defina GEMINI_API_KEY no ambiente. Ex: export GEMINI_API_KEY='...'}"

echo "[run_reel] Rodando pipeline para URL: $URL"
python -m reel_analyzer.cli \
  --url "$URL" \
  --i-own-this \
  --gemini-api-key "$GEMINI_API_KEY" \
  --tesseract-cmd "$TESS" \
  --ocr-langs "por+eng" \
  --vision \
  --out results/analysis.json

echo "[run_reel] Preview rápido (Gemini + OCR)..."
python - << 'EOF'
import json, textwrap
d = json.load(open("results/analysis.json", "r", encoding="utf-8"))

txt = d.get("gemini", {}).get("text_analysis", {}).get("raw", "") or ""
ocr = d.get("ocr", {}).get("consolidated_text", "") or ""

print("\n===== RESUMO GEMINI (raw) =====\n")
print(textwrap.shorten(txt.replace("\n", " "), width=800, placeholder=" ..."))

print("\n\n===== TRECHO OCR (até 800 chars) =====\n")
print(ocr[:800])
EOF

echo "[run_reel] Exportando para Google Docs..."
python export_to_gdocs.py results/analysis.json --title "$TITLE"

echo "[run_reel] Fim."

python - << 'EOF'
import json, sys
d=json.load(open("results/analysis.json","r",encoding="utf-8"))
ok = d.get("gemini", {}).get("text_analysis", {}).get("ok", False)
if not ok:
    err = d.get("gemini", {}).get("text_analysis", {}).get("error", "erro desconhecido")
    print("\n[run_reel] ERRO: Gemini falhou, não vou exportar pro Docs.\n", err, "\n")
    sys.exit(2)
EOF
