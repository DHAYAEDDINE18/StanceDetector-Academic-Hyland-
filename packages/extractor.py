import re
import os

class ThesisExtractor:
    """
    Extracts thesis sections (Introduction, Methodology, etc.)
    from an extracted text file that includes both printed and PDF page numbers.
    Writes each section into the caller-provided out_dir and returns file paths.
    """

    def __init__(self, file_path, out_dir="extracted_sections"):
        self.file_path = file_path
        self.out_dir = out_dir  # use caller directory, not a hardcoded one
        self.lines = []
        self.page_map = {}
        self.page_markers = {}
        self.Mapped_TOC = []  # list[(title, printed, pdf_page)]

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        self._load_text()

    def _load_text(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.lines = f.readlines()

    def _extract_toc(self):
        TOC = []
        toc_started = False
        for line in self.lines:
            low = line.lower()
            if not toc_started and ("table of contents" in low or "contents" in low or "content" in low):
                toc_started = True
                continue
            if toc_started:
                if "references" in low or "bibliography" in low:
                    break
                if re.search(r"\.+\s*\d+", line):
                    TOC.append(line.strip())

        pairs = []
        for entry in TOC:
            m = re.match(r"^(.*?)\.{2,}\s*(\d+)$", entry)
            if m:
                title = m.group(1).strip()
                printed_page = int(m.group(2))
                pairs.append((title, printed_page))
        return pairs

    def _map_pages(self):
        current_pdf_page = None
        for line in self.lines:
            m_pdf = re.search(r"---\s*page\s*(\d+)\s*---", line.lower())
            if m_pdf:
                current_pdf_page = int(m_pdf.group(1))
                continue
            m_print = re.match(r"^\s*(\d{1,3})\s*$", line.strip())
            if m_print and current_pdf_page is not None:
                printed_num = int(m_print.group(1))
                self.page_map.setdefault(printed_num, current_pdf_page)

    def _align_toc(self, toc_pairs):
        self.Mapped_TOC = []
        for title, printed in toc_pairs:
            pdf_page = self.page_map.get(printed)
            if pdf_page is not None:
                self.Mapped_TOC.append((title, printed, pdf_page))
        self.Mapped_TOC.sort(key=lambda x: x[2])

    def _get_page_markers(self):
        for idx, line in enumerate(self.lines):
            m = re.search(r"---\s*page\s*(\d+)\s*---", line.lower())
            if m:
                self.page_markers[int(m.group(1))] = idx

    def _clean_title(self, title: str) -> str:
        return re.sub(r"[^A-Za-z0-9_\- ]+", "", title).strip().replace(" ", "_")

    def extract_sections(self):
        """
        Returns: list of tuples (title, printed_page, pdf_page, file_path)
        """
        toc = self._extract_toc()
        self._map_pages()
        self._align_toc(toc)
        self._get_page_markers()

        os.makedirs(self.out_dir, exist_ok=True)

        results = []
        for i, (title, printed, pdf_page) in enumerate(self.Mapped_TOC):
            start_idx = self.page_markers.get(pdf_page)
            if start_idx is None:
                continue
            end_idx = (
                self.page_markers.get(self.Mapped_TOC[i + 1][2])
                if i + 1 < len(self.Mapped_TOC)
                else len(self.lines)
            )
            section_text = "".join(self.lines[start_idx:end_idx])
            clean_title = self._clean_title(title)
            file_path = os.path.join(self.out_dir, f"{clean_title}.txt")
            with open(file_path, "w", encoding="utf-8") as f_out:
                f_out.write(section_text)
            print(f"✅ Saved section: {title} → {file_path}")
            results.append((title, printed, pdf_page, file_path))

        print("\n🎉 All sections extracted successfully!")
        return results
