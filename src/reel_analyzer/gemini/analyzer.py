import logging, time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


# --------- SCHEMAS ----------
class VideoExtraction(BaseModel):
    audio_transcript: str = Field(
        default="", description="Transcrição verbatim do áudio com timestamps."
    )
    on_screen_text: str = Field(
        default="",
        description="Texto em tela (OCR) em ordem cronológica com timestamps.",
    )
    blog_article: str = Field(
        default="", description="Artigo de blog baseado no áudio."
    )
    language: str = Field(default="pt-BR")
    notes: List[str] = Field(default_factory=list)
    confidence: int = Field(
        default=50, description="0-100: confiança geral na extração."
    )


class ReelAnalysis(BaseModel):
    resumo: str
    topicos_principais: List[str] = Field(default_factory=list)
    sentimento: str
    palavras_chave: List[str] = Field(default_factory=list)
    publico_alvo_provavel: List[str] = Field(default_factory=list)
    estrategias_marketing: List[str] = Field(default_factory=list)
    ctas: List[str] = Field(default_factory=list)
    viralidade_potencial: str
    sugestoes_melhoria: List[str] = Field(default_factory=list)


# --------- CONFIG ----------
@dataclass
class GeminiConfig:
    model_text: str = "gemini-2.5-flash"
    model_video: str = "gemini-2.5-flash"
    model_vision: str = "gemini-2.5-flash"
    temperature: float = 0.3

    # “limitador” de saída (resposta): aumenta/diminui aqui
    max_output_tokens_text: int = 2048
    max_output_tokens_video: int = 8192

    # Evita 429 com quota=0 no PRO
    allow_pro: bool = False


def pick_model(prompt: str, cfg: GeminiConfig) -> str:
    long_kw = [
        "transcrição",
        "verbatim",
        "palavra por palavra",
        "artigo",
        "blog",
        "detailed",
        "explicação longa",
    ]
    wants_long = any(k in (prompt or "").lower() for k in long_kw)
    if wants_long and cfg.allow_pro:
        return "gemini-2.5-pro"
    return cfg.model_text  # (flash por padrão)


class GeminiAnalyzer:
    def __init__(
        self, api_key: Optional[str] = None, cfg: Optional[GeminiConfig] = None
    ):
        self.cfg = cfg or GeminiConfig()
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def _wait_until_active(self, uploaded, timeout_s: int = 300, poll_s: float = 2.0):
        """
        IMPORTANTe: checa o estado via files.get (recomendado na doc) e normaliza enum -> string.
        """
        t0 = time.time()
        while True:
            cur = self.client.files.get(
                name=uploaded.name
            )  # doc: use files.get p/ checar metadata/state
            state = getattr(cur, "state", None)

            # Normaliza: FileState.ACTIVE -> "ACTIVE"
            state_name = getattr(state, "name", None) or str(state).split(".")[-1]
            state_name = (state_name or "").upper()

            if state_name == "ACTIVE":
                return cur

            if time.time() - t0 > timeout_s:
                raise TimeoutError(
                    f"Arquivo não ficou ACTIVE em {timeout_s}s (state={state})"
                )

            time.sleep(poll_s)

    def extract_from_video(
        self, video_path: str, *, extra_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        prompt = (
            "Retorne APENAS um JSON compatível com o schema.\n"
            "Idioma: pt-BR.\n\n"
            "1) audio_transcript:\n"
            "- Transcrição VERBATIM (palavra por palavra), mantendo gírias e repetições.\n"
            "- Use Falante 1, Falante 2...\n"
            "- Inclua timestamps a cada troca de falante OU a cada 30s.\n\n"
            "2) on_screen_text:\n"
            "- OCR do texto em tela em ordem cronológica.\n"
            "- Inclua timestamps/intervalos; marque [ILEGÍVEL] e [INCERTO] quando necessário.\n\n"
            "3) blog_article:\n"
            "- Artigo completo baseado no áudio; use '##' e '###' e bullets quando fizer sentido.\n"
            "- Sem inventar fatos; se inferir, marque [HIPÓTESE].\n"
        )
        if extra_instructions:
            prompt += f"\nInstruções extras:\n{extra_instructions.strip()}\n"

        try:
            uploaded = self.client.files.upload(file=video_path)
            uploaded = self._wait_until_active(uploaded, timeout_s=300, poll_s=2.0)

            resp = self.client.models.generate_content(
                model=self.cfg.model_video,
                contents=[uploaded, prompt],
                config=types.GenerateContentConfig(
                    temperature=self.cfg.temperature,
                    max_output_tokens=self.cfg.max_output_tokens_video,
                    response_mime_type="application/json",
                    response_schema=VideoExtraction,
                ),
            )
            return {"ok": True, "raw": resp.text, "parsed": self._safe_json(resp.text)}
        except Exception as e:
            log.exception("Gemini video extraction falhou: %s", e)
            return {"ok": False, "error": str(e)}

    def analyze_text(
        self, text: str, *, extra_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        base = (
            "Você é um analista de conteúdo. Baseado SOMENTE no texto abaixo (OCR+trechos), "
            "liste 5 Key Takeaways com timestamp se existir; se não existir, marque INCERTO.\n"
            "Responda em pt-BR e SEM inventar.\n"
        )
        if extra_instructions:
            base += f"\nInstruções extras:\n{extra_instructions.strip()}\n"
        base += "\nTEXTO:\n" + (text or "")[:12000]

        try:
            model_to_use = pick_model(base, self.cfg)  # <- aqui é o lugar certo
            resp = self.client.models.generate_content(
                model=model_to_use,
                contents=base,
                config=types.GenerateContentConfig(
                    temperature=self.cfg.temperature,
                    max_output_tokens=self.cfg.max_output_tokens_text,
                    response_mime_type="application/json",
                    response_schema=ReelAnalysis,
                ),
            )
            return {"ok": True, "raw": resp.text, "parsed": self._safe_json(resp.text)}
        except Exception as e:
            log.exception("Gemini text analysis falhou: %s", e)
            return {"ok": False, "error": str(e)}

    def analyze_vision(
        self, prompt: str, image_bytes_list: List[bytes], mime_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
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
