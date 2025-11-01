# packages/gemini_validator/config.py
import os
ALLOWED_STANCE = {"self_mention","hedging","boosting"}
REQUIRED_COLS = ["sentence","stance_type","cue","start","end"]
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
ENV_API_KEY = "GEMINI_API_KEY"
CACHE_PATH = ".gemini_hyland_cache.jsonl"
