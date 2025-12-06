Reel Gemini Analyzer

Pipeline de análise de vídeos curtos (ex.: Reels) que:

baixa o vídeo via yt-dlp (ou usa um .mp4 local)

extrai frames

faz OCR com Tesseract (texto na tela)

(opcional) transcreve o áudio com Whisper

analisa com Gemini (texto e opcionalmente vision)

salva tudo em results/analysis.json

exporta o resultado para Google Docs

Uso responsável: utilize apenas conteúdo que você possui ou tem permissão para analisar/baixar.

Requisitos

Python 3.13+

Tesseract OCR instalado (Windows)

Opcional (para transcrição de áudio):

ffmpeg no PATH

torch + openai-whisper

Opcional (para exportar para Google Docs):

Google Docs API habilitada no seu projeto do Google Cloud

OAuth credentials.json

Instalação (Windows + Git Bash)

Na pasta do projeto:

py -3.13 -m venv .venv
source .venv/Scripts/activate
python -m pip install -U pip
pip install -e .


Teste se está OK:

reel-analyze --help
python -c "import cv2, numpy, pytesseract; print('cv2', cv2.__version__, '| numpy', numpy.__version__)"

Configurar Gemini API Key

Você pode passar no comando:

--gemini-api-key "SUA_CHAVE"


Ou setar variável de ambiente (recomendado):

PowerShell (sessão atual):

$env:GEMINI_API_KEY="SUA_CHAVE"


Permanente (Windows):

setx GEMINI_API_KEY "SUA_CHAVE"


O código aceita GEMINI_API_KEY ou GOOGLE_API_KEY.

Tesseract (Windows)

Se você já instalou em:

D:\Usuarios\08853011106\AppData\Local\Programs\Tesseract-OCR\tesseract.exe

No Git Bash, use assim:

--tesseract-cmd "/d/Usuarios/08853011106/AppData/Local/Programs/Tesseract-OCR/tesseract.exe"


Verifique:

"/d/Usuarios/08853011106/AppData/Local/Programs/Tesseract-OCR/tesseract.exe" --version

Rodar análise (URL)
source .venv/Scripts/activate

python -m reel_analyzer.cli \
  --url "https://www.instagram.com/reel/SEU_ID_AQUI/" \
  --i-own-this \
  --gemini-api-key "$GEMINI_API_KEY" \
  --tesseract-cmd "/d/Usuarios/08853011106/AppData/Local/Programs/Tesseract-OCR/tesseract.exe" \
  --ocr-langs "por+eng" \
  --vision \
  --out results/analysis.json


Mostrar resumo rápido:

python -c "import json; d=json.load(open('results/analysis.json','r',encoding='utf-8')); print(d['gemini']['text_analysis'].get('raw','')); print('\n---\n'); print((d.get('ocr') or {}).get('consolidated_text','')[:800])"

Rodar análise (vídeo local)
python -m reel_analyzer.cli \
  --video "caminho/para/video.mp4" \
  --gemini-api-key "$GEMINI_API_KEY" \
  --tesseract-cmd "/d/Usuarios/08853011106/AppData/Local/Programs/Tesseract-OCR/tesseract.exe" \
  --ocr-langs "por+eng" \
  --out results/analysis.json

Transcrição de áudio (Whisper)

Se o seu projeto já está com o pipeline chamando Whisper automaticamente quando instalado:

1) Instale dependências
pip install torch openai-whisper

2) Instale o ffmpeg

Garanta que ffmpeg -version funcione no terminal.

Se Whisper/ffmpeg não estiverem instalados, o pipeline deve pular áudio e seguir só com OCR.

Exportar para Google Docs
1) Instale libs do Google no venv
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

2) Habilite a Google Docs API

No Google Cloud Console:

selecione seu projeto

APIs & Services → Library → Google Docs API → Enable

Se estiver desabilitada, você verá erro 403 “SERVICE_DISABLED”.

3) OAuth (credentials.json)

No Google Cloud Console:

APIs & Services → Credentials → Create Credentials → OAuth client ID

Tipo: Desktop app

Baixe o JSON e salve como credentials.json na raiz do projeto (mesma pasta do export_to_gdocs.py).

Se der 403 access_denied: no OAuth consent screen, em Testing, adicione seu e-mail em Test users.

4) Exportar
python export_to_gdocs.py results/analysis.json --title "Reels SEU_ID"


Na primeira vez, vai abrir o navegador para autenticar e criar token.json.

Script único (terminal)

Crie um arquivo run_all.sh na raiz:

cat > run_all.sh <<'EOF'
#!/usr/bin/env bash
set -e

URL="$1"
TITLE="$2"

if [ -z "$URL" ]; then
  echo "Uso: ./run_all.sh <URL> <TITULO>"
  exit 1
fi

if [ -z "$TITLE" ]; then
  TITLE="Reels"
fi

source .venv/Scripts/activate

python -m reel_analyzer.cli \
  --url "$URL" \
  --i-own-this \
  --gemini-api-key "$GEMINI_API_KEY" \
  --tesseract-cmd "/d/Usuarios/08853011106/AppData/Local/Programs/Tesseract-OCR/tesseract.exe" \
  --ocr-langs "por+eng" \
  --vision \
  --out results/analysis.json

python -c "import json; d=json.load(open('results/analysis.json','r',encoding='utf-8')); print(d['gemini']['text_analysis'].get('raw','')); print('\n---\n'); print((d.get('ocr') or {}).get('consolidated_text','')[:800])"

python export_to_gdocs.py results/analysis.json --title "$TITLE"
EOF

chmod +x run_all.sh


Uso:

./run_all.sh "https://www.instagram.com/reel/SEU_ID_AQUI/" "Reels SEU_ID"

Troubleshooting (clássicos)
reel-analyze: command not found

venv não ativado, ou o entrypoint não entrou no PATH.

Solução: source .venv/Scripts/activate e rode python -m reel_analyzer.cli ...

tesseract: command not found / OCR falha

Tesseract não instalado ou sem PATH.

Solução: use --tesseract-cmd ".../tesseract.exe"

Gemini: Missing key inputs argument

API key não foi passada e não está em env.

Solução: --gemini-api-key "..." ou set GEMINI_API_KEY.

Google Docs: 403 SERVICE_DISABLED

Google Docs API desabilitada no projeto.

Solução: habilitar a API no Cloud Console.

OAuth 403 access_denied

App em Testing e sua conta não está como test user.

Solução: OAuth consent screen → Test users → adicione seu e-mail.