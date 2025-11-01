# packages/nltk_stance/stance_detector.py
import csv, os, re
from typing import List, Dict, Tuple
from nltk import pos_tag
from nltk.stem import WordNetLemmatizer

from packages.nltk_stance.preprocessor import TextPreprocessor
from packages.nltk_stance.stance_lexicon import STANCE_LEXICON

# Optional: sections/headings typically not argumentative
SECTION_EXCLUDE = {
    "abstract", "table of contents", "acknowledgements",
    "references", "appendices", "list of tables", "list of figures"
}

# Promote multiword cues to explicit patterns
MULTIWORD = {
    "boosting": [
        ["it", "is", "clear", "that"],
        ["it", "is", "evident", "that"]
    ],
    "attitude": [
        ["it", "is", "important", "to", "note"],
        ["it", "is", "surprising", "that"]
    ]
}

# Lemma-normalized unigrams with coarse POS gating
LEMMA_UNIGRAMS = {
    "boosting": {"show", "prove", "demonstrate", "indicate", "evidence"},
    "hedging": {"may", "might", "could", "seem", "appear", "suggest", "approximately", "generally", "likely", "perhaps"},
    "attitude": {"unfortunately", "importantly", "surprisingly", "interestingly"},
    "self_mention": {"i", "we", "our", "my", "us"}
}

class StanceDetector:
    def __init__(self, text, section_name: str = None, page: int = None):
        self.preprocessor = TextPreprocessor(text)
        self.sentences = self.preprocessor.tokenize_sentences()
        self.section_name = section_name
        self.page = page
        self._wnl = WordNetLemmatizer()

    # ---------- Internal helpers ----------
    def _exclude_sentence(self, sent: str) -> bool:
        low = sent.strip().lower()
        if not low:
            return True
        # Skip headings/front/back matter by keywords or very short all-caps lines
        if len(sent) < 8 and sent.isupper():
            return True
        for h in SECTION_EXCLUDE:
            if h in low[:120]:
                return True
        # Skip captions/citation-only lines
        if re.search(r"^(figure|table)\s+\d+|^\(?\d{4}\)?$|^\[\d+\]$", low):
            return True
        # Skip page banners like --- Page 2 ---
        if re.search(r"-{2,}\s*page\s+\d+\s*-{2,}", low):
            return True
        return False

    def _negated_window(self, tokens: List[str], idx: int, window: int = 3) -> bool:
        start = max(0, idx - window)
        seg = [t.lower() for t in tokens[start: idx + 1]]
        return any(n in seg for n in ("not", "n't", "no", "never", "cannot", "can’t", "can´t"))

    def _lemmatize(self, token: str, pos_tag_: str) -> str:
        pos = 'v' if pos_tag_.startswith('V') else 'n' if pos_tag_.startswith('N') else 'a' if pos_tag_.startswith('J') else 'r'
        return self._wnl.lemmatize(token.lower(), pos=pos)

    def _match_multiword(self, tokens: List[str]) -> List[Tuple[str, str, int, int]]:
        hits = []
        low = [t.lower() for t in tokens]
        for stype, patterns in MULTIWORD.items():
            for pat in patterns:
                n = len(pat)
                for i in range(len(low) - n + 1):
                    if low[i:i+n] == pat and not self._negated_window(low, i + n - 1):
                        hits.append((stype, " ".join(pat), i, i+n))
        return hits

    def _match_unigrams(self, tokens: List[str], tags: List[str]) -> List[Tuple[str, str, int, int]]:
        hits = []
        lows = [t.lower() for t in tokens]
        lemmas = [self._lemmatize(tok, pos) for tok, pos in zip(tokens, tags)]
        for i, (tok, low, lem, pos) in enumerate(zip(tokens, lows, lemmas, tags)):
            # Self-mention: prefer standalone pronouns (PRP/PRP$) and sentence-initial positions
            if low in LEMMA_UNIGRAMS["self_mention"]:
                if pos.startswith("PRP") or i == 0:
                    hits.append(("self_mention", low, i, i+1))
                continue
            for stype, lex in LEMMA_UNIGRAMS.items():
                if stype == "self_mention":
                    continue
                # Gate some classes by POS to reduce noise
                if stype in {"boosting", "hedging"} and not (pos.startswith("V") or pos in {"MD", "RB", "JJ"}):
                    continue
                if lem in lex or low in lex:
                    if not self._negated_window(lows, i):
                        hits.append((stype, low, i, i+1))
        return hits

    # ---------- Public API ----------
    def detect_stance_markers(self) -> List[Dict]:
        results = []
        for sent in self.sentences:
            if self._exclude_sentence(sent):
                continue
            tokens = self.preprocessor.tokenize_words(sent)
            if not tokens:
                continue
            # POS tag the sentence
            pos_tags = [t for _, t in pos_tag(tokens)]
            # Collect hits
            spans = {}
            for stype, cue, s, e in self._match_multiword(tokens):
                spans[(s, e, stype, cue)] = (stype, cue, s, e)
            for stype, cue, s, e in self._match_unigrams(tokens, pos_tags):
                spans.setdefault((s, e, stype, cue), (stype, cue, s, e))
            if spans:
                markers = [{"stance_type": stype, "cue": cue, "start": s, "end": e}
                           for (_, _, stype, cue), (stype, cue, s, e) in spans.items()]
                results.append({
                    "sentence": sent,
                    "markers": markers,
                    "section": self.section_name,
                    "page": self.page
                })
        return results

    def count_stance_types(self) -> Dict[str, int]:
        counts = {"hedging": 0, "boosting": 0, "attitude": 0, "self_mention": 0}
        for item in self.detect_stance_markers():
            for m in item["markers"]:
                counts[m["stance_type"]] += 1
        return counts

    def export_to_csv(self, filename: str = "output/stance_results.csv"):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        rows = []
        for item in self.detect_stance_markers():
            sent = item["sentence"]
            section = item.get("section")
            page = item.get("page")
            for m in item["markers"]:
                rows.append({
                    "sentence": sent,
                    "stance_type": m["stance_type"],
                    "cue": m["cue"],
                    "start": m["start"],
                    "end": m["end"],
                    "section": section,
                    "page": page
                })
        fieldnames = ["sentence", "stance_type", "cue", "start", "end", "section", "page"]
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
