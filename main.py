# gui_main.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
import os
import re

# Match main.py import style
from packages.pdf_to_text import PDFExtractor
from packages.nltk_stance import StanceDetector
from packages import ThesisExtractor

# Optional: Gemini validator import (safe if package missing)
try:
    from packages.gemini_validator import validate_file as gemini_validate_file
except Exception:
    gemini_validate_file = None

class StanceGUI(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.master = master
        self.master.title("Thesis Stance Detector")
        self.master.minsize(980, 640)

        # ======= State =======
        self.pdf_dir_var = tk.StringVar()
        self.extracted_dir_var = tk.StringVar(value="extracted_txt")

        self.thesis_text_for_sections_var = tk.StringVar()  # thesis text to divide
        self.sections_out_dir_var = tk.StringVar(value="extracted_sections")
        self.section_map = []  # list of (title, printed, pdf_page)
        self.section_files = []  # paths corresponding to titles post-extraction
        self.selected_section_index = tk.IntVar(value=-1)

        self.section_file_var = tk.StringVar()   # directly chosen section file (optional)
        self.input_path_var = tk.StringVar(value=os.path.join("extracted_txt", "thesis_access1.txt"))
        self.output_path_var = tk.StringVar(value=os.path.join("output", "General_Conclusion_stance.csv"))
        self.preview_count_var = tk.IntVar(value=5)

        # NEW: AI validation controls
        self.use_ai_validate_var = tk.BooleanVar(value=False)
        self.gemini_model_var = tk.StringVar(value="gemini-1.5-pro")
        self.gemini_api_key_var = tk.StringVar(value=os.environ.get("GEMINI_API_KEY", ""))

        # =========== PDF Extraction ===========
        pdf_frame = ttk.LabelFrame(self, text="PDF Extraction")
        self.pdf_dir_entry = ttk.Entry(pdf_frame, textvariable=self.pdf_dir_var, width=60)
        self.pdf_dir_btn = ttk.Button(pdf_frame, text="Choose PDF Folder", command=self.choose_pdf_dir)
        self.extracted_dir_lbl = ttk.Label(pdf_frame, text="Output dir (txt):")
        self.extracted_dir_entry = ttk.Entry(pdf_frame, textvariable=self.extracted_dir_var, width=40)
        self.extract_btn = ttk.Button(pdf_frame, text="Extract PDFs → Text", command=self.extract_pdfs)
        self.pdf_dir_entry.grid(row=0, column=0, sticky="ew", padx=(0,6), pady=4)
        self.pdf_dir_btn.grid(row=0, column=1, sticky="w", pady=4)
        self.extracted_dir_lbl.grid(row=1, column=0, sticky="w", pady=2)
        self.extracted_dir_entry.grid(row=1, column=1, sticky="ew", pady=2)
        self.extract_btn.grid(row=0, column=2, rowspan=2, sticky="nsw", padx=(8,0))
        pdf_frame.columnconfigure(0, weight=1)

        # =========== Divide Thesis into Sections ===========
        divide_frame = ttk.LabelFrame(self, text="Divide Thesis into Sections")
        self.thesis_text_entry = ttk.Entry(divide_frame, textvariable=self.thesis_text_for_sections_var, width=60)
        self.thesis_text_btn = ttk.Button(divide_frame, text="Choose Thesis Text", command=self.choose_thesis_text)
        self.sections_out_lbl = ttk.Label(divide_frame, text="Sections dir:")
        self.sections_out_entry = ttk.Entry(divide_frame, textvariable=self.sections_out_dir_var, width=40)
        self.divide_btn = ttk.Button(divide_frame, text="Extract Sections", command=self.divide_sections)
        self.thesis_text_entry.grid(row=0, column=0, sticky="ew", padx=(0,6), pady=4)
        self.thesis_text_btn.grid(row=0, column=1, sticky="w", pady=4)
        self.sections_out_lbl.grid(row=1, column=0, sticky="w", pady=2)
        self.sections_out_entry.grid(row=1, column=1, sticky="ew", pady=2)
        self.divide_btn.grid(row=0, column=2, rowspan=2, sticky="nsw", padx=(8,0))
        divide_frame.columnconfigure(0, weight=1)

        # =========== Sections Browser ===========
        browser_frame = ttk.LabelFrame(self, text="Sections Browser")
        self.sections_list = tk.Listbox(browser_frame, height=10, exportselection=False)
        self.sections_scroll = ttk.Scrollbar(browser_frame, orient="vertical", command=self.sections_list.yview)
        self.sections_list.configure(yscrollcommand=self.sections_scroll.set)
        self.load_section_btn = ttk.Button(browser_frame, text="Load Selected Section", command=self.load_selected_section)
        self.preview_section_btn = ttk.Button(browser_frame, text="Preview Selected", command=self.preview_selected_section)
        self.sections_list.grid(row=0, column=0, sticky="nsew", padx=(0,6), pady=(4,4))
        self.sections_scroll.grid(row=0, column=1, sticky="ns", pady=(4,4))
        self.load_section_btn.grid(row=1, column=0, sticky="w", pady=(0,4))
        self.preview_section_btn.grid(row=1, column=0, sticky="e", pady=(0,4))
        browser_frame.columnconfigure(0, weight=1)
        browser_frame.rowconfigure(0, weight=1)

        # =========== Pick Section File (optional) ===========
        pick_section_frame = ttk.LabelFrame(self, text="Pick Section File (optional)")
        self.section_entry = ttk.Entry(pick_section_frame, textvariable=self.section_file_var, width=60)
        self.section_browse = ttk.Button(pick_section_frame, text="Choose .txt Section", command=self.choose_section_file)
        self.section_info = ttk.Label(pick_section_frame, text="You can select any section .txt; it will be used as input below.")
        self.section_entry.grid(row=0, column=0, sticky="ew", padx=(0,6), pady=4)
        self.section_browse.grid(row=0, column=1, sticky="w", pady=4)
        self.section_info.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0,4))
        pick_section_frame.columnconfigure(0, weight=1)

        # =========== Stance Detection I/O ===========
        io_frame = ttk.LabelFrame(self, text="Stance Detection I/O")
        self.input_label = ttk.Label(io_frame, text="Input text file:")
        self.input_entry = ttk.Entry(io_frame, textvariable=self.input_path_var)
        self.input_browse = ttk.Button(io_frame, text="Browse", command=self.browse_input)

        self.output_label = ttk.Label(io_frame, text="Output CSV:")
        self.output_entry = ttk.Entry(io_frame, textvariable=self.output_path_var)
        self.output_browse = ttk.Button(io_frame, text="Save As", command=self.browse_output)

        self.preview_label = ttk.Label(io_frame, text="Preview detections:")
        self.preview_spin = ttk.Spinbox(io_frame, from_=1, to=2000, textvariable=self.preview_count_var, width=8)

        # AI validation controls
        self.use_ai_chk = ttk.Checkbutton(io_frame, text="Validate with AI (Gemini)", variable=self.use_ai_validate_var)
        self.model_lbl = ttk.Label(io_frame, text="Gemini model:")
        self.model_box = ttk.Combobox(io_frame, textvariable=self.gemini_model_var, width=24,
                                      values=["gemini-1.5-pro","gemini-1.5-flash","gemini-1.5-flash-8b"])
        self.api_lbl = ttk.Label(io_frame, text="API key:")
        self.api_entry = ttk.Entry(io_frame, textvariable=self.gemini_api_key_var, width=36, show="*")

        self.input_label.grid(row=0, column=0, sticky="w", pady=(2,2))
        self.input_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0,6))
        self.input_browse.grid(row=1, column=2, sticky="e")

        self.output_label.grid(row=2, column=0, sticky="w", pady=(8,2))
        self.output_entry.grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0,6))
        self.output_browse.grid(row=3, column=2, sticky="e")

        self.preview_label.grid(row=4, column=0, sticky="w", pady=(8,2))
        self.preview_spin.grid(row=4, column=1, sticky="w")

        self.use_ai_chk.grid(row=5, column=0, sticky="w", pady=(12,2))
        self.model_lbl.grid(row=6, column=0, sticky="w")
        self.model_box.grid(row=6, column=1, sticky="w")
        self.api_lbl.grid(row=7, column=0, sticky="w")
        self.api_entry.grid(row=7, column=1, sticky="ew")
        io_frame.columnconfigure(0, weight=1)

        # =========== Actions and Status ===========
        self.run_button = ttk.Button(self, text="Run Stance Detection", command=self.run_detection)
        self.preview_button = ttk.Button(self, text="Preview", command=self.preview_detections)
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self, textvariable=self.status_var)

        # =========== Output ===========
        self.output_text = tk.Text(self, height=14, wrap="word", state="disabled")
        self.output_scroll = ttk.Scrollbar(self, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=self.output_scroll.set)

        # =========== Layout root ===========
        pdf_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
        divide_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8,0))
        browser_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(8,0))
        pick_section_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8,0))
        io_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8,0))

        self.run_button.grid(row=5, column=0, sticky="w", pady=(10,6))
        self.preview_button.grid(row=5, column=1, sticky="w", pady=(10,6))
        self.progress.grid(row=5, column=2, sticky="ew", pady=(10,6))

        self.output_text.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(8,0))
        self.output_scroll.grid(row=6, column=3, sticky="ns", pady=(8,0))

        self.status_label.grid(row=7, column=0, columnspan=3, sticky="w", pady=(8,0))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(6, weight=2)

        self.last_markers = None

    # ===== Common UI helpers =====
    def set_busy(self, busy=True, status="Working..."):
        if busy:
            self.progress.start(10)
            self.run_button.config(state="disabled")
            self.preview_button.config(state="disabled")
            self.status_var.set(status)
        else:
            self.progress.stop()
            self.run_button.config(state="normal")
            self.preview_button.config(state="normal")
            self.status_var.set(status or "Ready")

    def write_output(self, text):
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("end", text)
        self.output_text.config(state="disabled")

    # ===== PDF Extraction =====
    def choose_pdf_dir(self):
        path = filedialog.askdirectory(title="Select folder with PDFs")
        if path:
            self.pdf_dir_var.set(path)

    def extract_pdfs(self):
        pdf_dir = self.pdf_dir_var.get().strip()
        out_dir = self.extracted_dir_var.get().strip() or "extracted_txt"
        if not pdf_dir or not os.path.isdir(pdf_dir):
            messagebox.showwarning("PDF folder", "Please choose a valid folder containing PDFs.")
            return
        os.makedirs(out_dir, exist_ok=True)

        def worker():
            try:
                extractor = PDFExtractor(directory=pdf_dir)
                extractor.extract_multiple()
            except Exception as e:
                self.master.after(0, lambda: messagebox.showerror("Extraction error", str(e)))
                self.master.after(0, lambda: self.set_busy(False, "Extraction failed"))
                return
            self.master.after(0, lambda: self.set_busy(False, f"Extraction completed."))
            self.master.after(0, lambda: self.write_output(f"PDF extraction finished.\nSource: {pdf_dir}\nOutput dir: {out_dir}"))

        self.set_busy(True, "Extracting PDFs...")
        Thread(target=worker, daemon=True).start()

    # ===== Divide into Sections =====
    def choose_thesis_text(self):
        path = filedialog.askopenfilename(
            title="Select thesis text (full)",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.thesis_text_for_sections_var.set(path)

    def divide_sections(self):
        thesis_path = self.thesis_text_for_sections_var.get().strip()
        out_dir = self.sections_out_dir_var.get().strip() or "extracted_sections"
        if not thesis_path or not os.path.isfile(thesis_path):
            messagebox.showwarning("Thesis text", "Please select a valid thesis text file to divide.")
            return

        os.makedirs(out_dir, exist_ok=True)

        def worker():
            try:
                # Pass the selected out_dir to the extractor
                extractor = ThesisExtractor(thesis_path, out_dir=out_dir)

                # Expect: list of (title, printed, pdf_page, file_path)
                mapped = extractor.extract_sections()

                # Store real file paths for the list/browser
                files = [fp for (_t, _p, _pg, fp) in mapped]

            except Exception as e:
                self.master.after(0, lambda: messagebox.showerror("Section extraction error", str(e)))
                self.master.after(0, lambda: self.set_busy(False, "Section extraction failed"))
                return

            def finish():
                self.section_map = [(t, p, pg) for (t, p, pg, _fp) in mapped]
                self.section_files = files
                self._populate_sections_list()
                self.set_busy(False, f"Sections extracted: {len(mapped)}")
                self.write_output(f"Extracted {len(mapped)} sections into '{out_dir}'.\nSelect a section to load or preview.")
            self.master.after(0, finish)

        self.set_busy(True, "Extracting sections...")
        Thread(target=worker, daemon=True).start()

    def _clean_title_to_filename(self, title: str) -> str:
        clean = re.sub(r"[^A-Za-z0-9_\- ]+", "", title).strip().replace(" ", "_")
        return clean

    def _populate_sections_list(self):
        self.sections_list.delete(0, "end")
        for i, (title, printed, pdf_page) in enumerate(self.section_map):
            display = f"{i+1:02d}. {title}  (printed {printed} → pdf {pdf_page})"
            self.sections_list.insert("end", display)

    def _read_text_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def load_selected_section(self):
        sel = self.sections_list.curselection()
        if not sel:
            messagebox.showinfo("Select section", "Choose a section from the list.")
            return
        idx = sel[0]
        if idx < len(self.section_files) and os.path.isfile(self.section_files[idx]):
            self.input_path_var.set(self.section_files[idx])
            self.section_file_var.set(self.section_files[idx])
            self.status_var.set(f"Loaded section: {os.path.basename(self.section_files[idx])}")
        else:
            missing = self.section_files[idx] if idx < len(self.section_files) else "(out of range)"
            messagebox.showwarning("Missing file", f"Section file not found on disk:\n{missing}\nTry re-extracting or verify the sections folder.")

    def preview_selected_section(self):
        sel = self.sections_list.curselection()
        if not sel:
            messagebox.showinfo("Select section", "Choose a section from the list.")
            return
        idx = sel[0]
        if idx < len(self.section_files) and os.path.isfile(self.section_files[idx]):
            text = self._read_text_file(self.section_files[idx])
            snippet = text[:3000]
            self.write_output(snippet + ("\n...\n" if len(text) > len(snippet) else ""))
        else:
            messagebox.showwarning("Missing file", "Section file not found on disk. Try re-extracting.")

    # ===== Optional direct section picking =====
    def choose_section_file(self):
        path = filedialog.askopenfilename(
            title="Select extracted section file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.section_file_var.set(path)
            self.input_path_var.set(path)

    # ===== Stance Detection =====
    def browse_input(self):
        path = filedialog.askopenfilename(
            title="Select input text file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.input_path_var.set(path)

    def browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save CSV output",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.output_path_var.set(path)

    def _detect_in_background(self, text, output_csv):
        try:
            detector = StanceDetector(text)
            markers = detector.detect_stance_markers()
            if output_csv:
                # Ensure directory exists
                os.makedirs(os.path.dirname(output_csv), exist_ok=True)
                detector.export_to_csv(output_csv)

            # Optional Gemini validation pass
            if self.use_ai_validate_var.get() and gemini_validate_file is not None:
                api_key = self.gemini_api_key_var.get().strip()
                if api_key:
                    os.environ["GEMINI_API_KEY"] = api_key
                model_name = self.gemini_model_var.get().strip() or "gemini-1.5-pro"
                base, ext = os.path.splitext(output_csv or "output.csv")
                out_valid = f"{base}_validated{ext}"
                out_audit = f"{base}_audit{ext}"
                gemini_validate_file(output_csv, out_valid, out_audit, model_name=model_name)

        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.master.after(0, lambda: self.set_busy(False, "Error"))
            return

        def finish():
            self.last_markers = markers
            n = len(markers) if markers else 0
            msg = f"Completed. {n} detections."
            if self.use_ai_validate_var.get() and gemini_validate_file is not None:
                msg += " AI validation finished."
            self.set_busy(False, msg)
            self.show_preview()
        self.master.after(0, finish)

    def run_detection(self):
        path_in = self.input_path_var.get().strip()
        path_out = self.output_path_var.get().strip()
        if not path_in or not os.path.isfile(path_in):
            messagebox.showwarning("Missing input", "Please select a valid input text file.")
            return
        try:
            text = self._read_text_file(path_in)
        except Exception as e:
            messagebox.showerror("Read error", f"Failed to read input file:\n{e}")
            return

        self.set_busy(True, "Running stance detection...")
        Thread(target=self._detect_in_background, args=(text, path_out), daemon=True).start()

    def show_preview(self):
        if not self.last_markers:
            self.write_output("No results yet. Click Run Stance Detection first.")
            return
        n = max(1, int(self.preview_count_var.get() or 5))
        lines = []
        for m in self.last_markers[:n]:
            sent = m.get("sentence", "")
            tags = m.get("markers", [])
            lines.append(sent)
            lines.append(f"→ {tags}")
            lines.append("")
        self.write_output("\n".join(lines))

    def preview_detections(self):
        self.show_preview()

def main():
    root = tk.Tk()
    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass
    app = StanceGUI(root)
    app.grid(sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root.mainloop()

if __name__ == "__main__":
    main()
