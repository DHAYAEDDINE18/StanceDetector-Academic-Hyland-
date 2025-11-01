# packages/gemini_validator/cache.py
import os, json

class JsonlCache:
    def __init__(self, path: str):
        self.path = path
        self.mem = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                        self.mem[rec["key"]] = rec["value"]
                    except Exception:
                        pass

    def get(self, key):
        return self.mem.get(key)

    def set(self, key, value):
        self.mem[key] = value

    def flush(self):
        with open(self.path, "w", encoding="utf-8") as f:
            for k, v in self.mem.items():
                f.write(json.dumps({"key": k, "value": v}, ensure_ascii=False) + "\n")
