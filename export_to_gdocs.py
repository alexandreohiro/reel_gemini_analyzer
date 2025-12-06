import argparse, json, os
from datetime import datetime

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/documents"]

def load_text_from_result(path: str) -> str:
    data = json.load(open(path, "r", encoding="utf-8"))

    # tenta achar o texto “pronto pra docs” vindo do Gemini
    for p in [
        ("gemini", "text_analysis", "raw"),
        ("gemini", "analysis", "raw"),
        ("gemini_analysis", "analysis"),
        ("gemini_analysis", "raw"),
    ]:
        cur = data
        ok = True
        for k in p:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok and isinstance(cur, str) and cur.strip():
            return cur.strip()

    # fallback: junta OCR + qualquer campo textual
    ocr = ""
    if isinstance(data, dict):
        ocr = (
            data.get("ocr", {}).get("consolidated_text")
            or data.get("ocr_results", {}).get("consolidated_text")
            or ""
        )
    return (ocr or "INCERTO: não encontrei texto/análise no JSON.").strip()

def build_requests_from_markdownish(text: str, start_index: int = 1):
    """
    Interpreta linhas começando com '## ' e '### ' como headings,
    remove os hashes e aplica estilos no Google Docs.
    """
    lines = text.splitlines()
    cleaned_lines = []
    styles = []  # (range_start, range_end, namedStyleType)

    cursor = start_index
    for line in lines:
        style = "NORMAL_TEXT"
        clean = line

        if line.startswith("## "):
            style = "HEADING_1"
            clean = line[3:]
        elif line.startswith("### "):
            style = "HEADING_2"
            clean = line[4:]

        # garante newline (que fecha o parágrafo)
        clean_line = clean.rstrip()
        cleaned_lines.append(clean_line)

        # range pega o parágrafo todo (incluindo '\n')
        para_text = clean_line + "\n"
        range_start = cursor
        range_end = cursor + len(para_text)
        styles.append((range_start, range_end, style))

        cursor = range_end

    final_text = "\n".join(cleaned_lines).rstrip() + "\n"
    requests = [
        {"insertText": {"location": {"index": start_index}, "text": final_text}}
    ]

    # aplica estilo por parágrafo (heading/normal)
    for rs, re, st in styles:
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": rs, "endIndex": re},
                "paragraphStyle": {"namedStyleType": st},
                "fields": "namedStyleType",
            }
        })

    return requests

def get_creds():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return creds

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result_json", help="ex: results/analysis.json")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    text = load_text_from_result(args.result_json)
    title = args.title or f"Análise Reels {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    creds = get_creds()
    docs = build("docs", "v1", credentials=creds)

    doc = docs.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    requests = build_requests_from_markdownish(text, start_index=1)
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

    print("OK! Doc criado:", doc_id)
    print(f"Abrir: https://docs.google.com/document/d/{doc_id}/edit")

if __name__ == "__main__":
    main()
