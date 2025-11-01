# packages/gemini_validator/prompt.py
from .config import ALLOWED_STANCE

def normalize_stance(s: str) -> str:
    if not isinstance(s, str): return "hedging"
    s = s.strip().lower()
    if s in {"self-mention","selfmention"}: return "self_mention"
    if s in {"hedge"}: return "hedging"
    if s in {"booster"}: return "boosting"
    return s if s in ALLOWED_STANCE else "hedging"

def build_prompt(row: dict) -> str:
    sent = row.get("sentence","")
    cue = row.get("cue","")
    stance = normalize_stance(row.get("stance_type",""))
    start = row.get("start")
    end = row.get("end")
    return f"""
You validate Hyland-style stance annotations.

Return strict JSON:
- validated_stance_type: one of ["self_mention","hedging","boosting"]
- decision: one of ["keep","change","flag"]
- reasons: brief
- corrected_cue: string (echo cue or corrected surface form)
- offsets_ok: true/false

Rules:
- self_mention: first-person forms (I, we, my, our) or inclusive we.
- hedging: markers like may, might, seem, appear, suggest, probably.
- boosting: assertive markers like show/shown, prove/proved, clearly, obviously.

Check whether cue is a valid marker and appears in the sentence; if not, use decision="change" with corrected type or decision="flag" if uncertain.

INPUT:
sentence: {sent}
stance_type: {stance}
cue: {cue}
start: {start}
end: {end}
"""
