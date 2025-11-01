# packages/gemini_validator/cli.py
import argparse
from .validator import validate_file

def main():
    p = argparse.ArgumentParser(description="Validate Hyland stance CSV with Gemini")
    p.add_argument("--in", dest="input_csv", required=True)
    p.add_argument("--out", dest="output_csv", required=True)
    p.add_argument("--audit", dest="audit_csv", required=True)
    p.add_argument("--model", dest="model_name", default=None, help="Override model name")
    p.add_argument("--cache", dest="cache_path", default=None, help="Override cache path")
    args = p.parse_args()
    validate_file(args.input_csv, args.output_csv, args.audit_csv,
                  model_name=args.model_name or "gemini-1.5-pro",
                  cache_path=args.cache_path or ".gemini_hyland_cache.jsonl")

if __name__ == "__main__":
    main()
