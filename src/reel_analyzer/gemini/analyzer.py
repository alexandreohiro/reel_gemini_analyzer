import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

class ReelAnalysis(BaseModel):
    resumo: str = Field(..., description="Resumo conciso do conteúdo.")
    topicos_principais: List[str] = Field(default_factory=list)
    sentimento: str = Field(..., description="positivo, negativo, neutro ou misto")
    palavras_chave: List[str] = Field(default_factory=list)
    publico_alvo_provavel: List[str] = Field(default_factory=list)
    estrategias_marketing: List[str] = Field(default_factory=list)
    ctas: List[str] = Field(default_factory=list, description="Chamadas para ação")
    viralidade_potencial: str = Field(..., description="Avaliação qualitativa de viralidade")
    sugestoes_melhoria: List[str] = Field(default_factory=list)

@dataclass
class GeminiConfig:
    model_text: str = "gemini-2.5-flash"
    model_vision: str = "gemini-2.5-flash"
    temperature: float = 0.3

class GeminiAnalyzer:
    def __init__(self, api_key: Optional[str] = None, cfg: Optional[GeminiConfig] = None):
        self.cfg = cfg or GeminiConfig()
        # GEMINI_API_KEY ou GOOGLE_API_KEY podem ser usados
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = genai.Client()

    def analyze_text(self, text: str, *, extra_instructions: Optional[str] = None) -> Dict[str, Any]:
        BASE_PROMPT = (
    "Você é um analista de conteúdo rigoroso. Você recebeu TEXTO extraído por OCR de um vídeo curto "
    "(pode conter ruído, cortes, duplicações e erros).\n\n"

    "OBJETIVO: produzir um RELATÓRIO pronto para colar no Google Docs.\n\n"

    "REGRAS DURAS:\n"
    "1) Responda em PT-BR.\n"
    "2) Não invente fatos fora do OCR.\n"
    "3) Se faltar contexto, escreva explicitamente: INCERTO.\n"
    "4) Separe claramente: (a) o que está no OCR, (b) inferências, (c) coisas verificadas por pesquisa.\n"
    "5) Se o OCR contiver entidades consultáveis (nome de pessoa/empresa, lugar, evento, termo técnico, cifra, lei), "
    "use pesquisa para checar contexto SOMENTE desses itens.\n"
    "6) Se não houver entidades claras no OCR, NÃO pesquise: foque em qualidade do OCR e lacunas.\n\n"

    "MODO PESQUISA (quando aplicável):\n"
    "- Pesquise 1–3 consultas curtas e objetivas.\n"
    "- Traga só o que for diretamente relevante ao OCR.\n"
    "- Sempre inclua uma seção final '### Fontes (pesquisa)' com links.\n"
    "- Se não usar pesquisa, escreva: '### Fontes (pesquisa)\\n- (não usado)'.\n\n"

    "FORMATO (Google Docs-friendly):\n"
    "- Use títulos/subtítulos com '##' e '###'.\n"
    "- Use listas com '-'.\n"
    "- Parágrafos curtos.\n"
    "- NÃO use bloco de código.\n\n"

    "ESTRUTURA (siga exatamente):\n"
    "## Análise do Reels (OCR)\n"
    "### 1) Resumo\n"
    "### 2) Tese central (1 frase)\n"
    "### 3) Evidências textuais (citações do OCR)\n"
    "### 4) Tópicos principais\n"
    "### 5) Sentimento (positivo|negativo|neutro|misto|INCERTO)\n"
    "### 6) Público-alvo provável (com confiança 0–100 + evidência)\n"
    "### 7) Gatilhos psicológicos/persuasão (com confiança + evidência)\n"
    "### 8) CTAs (com tipo + evidência)\n"
    "### 9) Palavras-chave\n"
    "### 10) Riscos de interpretação / Lacunas\n"
    "### 11) Sugestões de melhoria\n"
    "### 12) Qualidade do OCR (nota 0–10 + problemas)\n"
    "### Fontes (pesquisa)\n\n"
        )


        if extra_instructions:
            prompt += f"Instruções extras:\n{extra_instructions.strip()}\n\n"

        prompt += f"TEXTO (OCR):\n{text[:12000]}"

        try:
            resp = self.client.models.generate_content(
                model=self.cfg.model_text,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.cfg.temperature,
                    max_output_tokens=self.cfg.max_output_tokens,
                    tools=[{"google_search": {}}, {"url_context": {}}],
                    response_mime_type="application/json",
                    response_schema=ReelAnalysis,
                ),
            )

            return {"ok": True, "raw": resp.text, "parsed": self._safe_json(resp.text)}
        except Exception as e:
            log.exception("Gemini text analysis falhou: %s", e)
            return {"ok": False, "error": str(e)}

    def analyze_vision(self, prompt: str, image_bytes_list: List[bytes], mime_type: str = "image/jpeg") -> Dict[str, Any]:
        parts = [types.Part.from_text(text=prompt)]
        for b in image_bytes_list:
            parts.append(types.Part.from_bytes(data=b, mime_type=mime_type))
        try:
            resp = self.client.models.generate_content(
                model=self.cfg.model_vision,
                contents=[types.UserContent(parts=parts)],
                config=types.GenerateContentConfig(temperature=self.cfg.temperature),
            )
            return {"ok": True, "text": resp.text}
        except Exception as e:
            log.exception("Gemini vision analysis falhou: %s", e)
            return {"ok": False, "error": str(e)}

    @staticmethod
    def _safe_json(s: str) -> Optional[Dict[str, Any]]:
        import json
        try:
            return json.loads(s)
        except Exception:
            return None
