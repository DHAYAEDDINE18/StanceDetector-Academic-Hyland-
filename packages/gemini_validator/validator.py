# packages/gemini_validator/validator.py
import os, json, hashlib
import pandas as pd
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.generativeai as genai

from .config import REQUIRED_COLS, ALLOWED_STANCE, DEFAULT_MODEL, ENV_API_KEY, CACHE_PATH
from .prompt import build_prompt, normalize_stance
from .cache import JsonlCache

def _hash_row(row, version="v1"):
    payload = json.dumps({
        "sentence": row.get("sentence",""),
        "stance_type": row.get("stance_type",""),
        "cue": row.get("cue",""),
        "start": int(row.get("start") if pd.notna(row.get("start")) else -1),
        "end": int(row.get("end") if pd.notna(row.get("end")) else -1),
        "section": row.get("section",""),
        "page": row.get("page","")
    }, ensure_ascii=False, sort_keys=True)
    return version + "_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=6),
       retry=retry_if_exception_type(Exception))
def _gemini_call(model, prompt):
    resp = model.generate_content(prompt)
    txt = resp.text.strip()
    i, j = txt.find("{"), txt.rfind("}")
    if i == -1 or j == -1:
        raise ValueError("No JSON in Gemini response")
    out = json.loads(txt[i:j+1])
    # guardrails
    val = out.get("validated_stance_type","hedging")
    out["validated_stance_type"] = val if val in ALLOWED_STANCE else "hedging"
    dec = out.get("decision","flag")
    out["decision"] = dec if dec in {"keep","change","flag"} else "flag"
    out["reasons"] = str(out.get("reasons",""))
    out["corrected_cue"] = str(out.get("corrected_cue",""))
    out["offsets_ok"] = bool(out.get("offsets_ok", False))
    return out

def validate_file(input_csv: str, output_csv: str, audit_csv: str, model_name: str = DEFAULT_MODEL, cache_path: str = CACHE_PATH):
    load_dotenv()
    api_key = os.getenv(ENV_API_KEY)
    if not api_key:
        raise RuntimeError(f"{ENV_API_KEY} is not set")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    df = pd.read_csv(input_csv)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["stance_type"] = df["stance_type"].map(normalize_stance)

    cache = JsonlCache(cache_path)
    audits, out_rows = [], []

    for idx, row in df.iterrows():
        row_d = row.to_dict()
        key = _hash_row(row_d)
        res = cache.get(key)
        if res is None:
            prompt = build_prompt(row_d)
            try:
                res = _gemini_call(model, prompt)
            except Exception as e:
                res = {"validated_stance_type":"hedging","decision":"flag","reasons":f"error:{type(e).__name__}",
                       "corrected_cue":row_d.get("cue",""),"offsets_ok":False}
            cache.set(key, res)

        new_row = row.copy()
        new_row["validated_stance_type"] = res["validated_stance_type"]
        new_row["decision"] = res["decision"]
        if res["decision"] in {"change","keep"} and res.get("corrected_cue"):
            new_row["cue"] = res["corrected_cue"]
        out_rows.append(new_row)

        audits.append({
            "row_index": idx,
            "stance_type_prior": row_d.get("stance_type"),
            "cue_prior": row_d.get("cue"),
            "start": row_d.get("start"),
            "end": row_d.get("end"),
            "validated_stance_type": res.get("validated_stance_type"),
            "corrected_cue": res.get("corrected_cue"),
            "offsets_ok": res.get("offsets_ok"),
            "decision": res.get("decision"),
            "reasons": res.get("reasons")
        })

    pd.DataFrame(out_rows).to_csv(output_csv, index=False)
    pd.DataFrame(audits).to_csv(audit_csv, index=False)
    cache.flush()
