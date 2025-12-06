# Reel → OCR → Gemini Analyzer (Projeto pronto em Python)

Este projeto faz **análise de vídeo** (especialmente Reels) em 3 etapas:
1) (Opcional) baixar o vídeo por URL (via yt-dlp)  
2) extrair frames e fazer **OCR (Tesseract)** para capturar texto na tela  
3) mandar o texto + (opcional) alguns frames para o **Gemini** e gerar uma análise

> Nota importante: o modo `--url` **só deve ser usado para conteúdo seu ou com permissão explícita**. Para qualquer outro caso, use `--video` (arquivo local).

## Requisitos
- Python 3.9+
- Tesseract instalado
  - Linux (Debian/Ubuntu): `sudo apt install tesseract-ocr tesseract-ocr-por`
  - Windows: instalador do Tesseract + configurar PATH (ou usar `--tesseract-cmd "C:\\...\\tesseract.exe"`)

## Instalação
```bash
# 1) Crie um venv (recomendado)
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

# 2) Instale as dependências
pip install -U pip
pip install -e .
```

## Configurar chave do Gemini
Defina a variável de ambiente:
```bash
# Linux/macOS
export GEMINI_API_KEY="AIzaSyCpIg6mEdI1d-a9cyQLoU8wGGbEnG9LR7k"

# Windows PowerShell
setx GEMINI_API_KEY "AIzaSyCpIg6mEdI1d-a9cyQLoU8wGGbEnG9LR7k"
```

## Uso rápido (arquivo local)
```bash
reel-analyze --video caminho/do/video.mp4 --out results/analysis.json
```

## Uso com visão (manda frames para o Gemini também)
```bash
reel-analyze --video video.mp4 --vision --frames 12 --out results/analysis.json
```

## Uso por URL (apenas se você possui permissão)
```bash
reel-analyze --url "https://www.instagram.com/reel/XXXXXXXX/" --i-own-this --out results/analysis.json
```

## Saída
O JSON final inclui:
- metadados do vídeo
- frames amostrados (paths)
- OCR consolidado + OCR por frame
- análise textual (Gemini)
- análise de visão (Gemini, opcional)

## Dicas
- Se o OCR vier fraco, aumente `--frames` ou use `--every-seconds 0.5`
- Experimente `--ocr-langs por+eng` (padrão) ou `eng` se o vídeo não for PT-BR

## Licença
MIT.
