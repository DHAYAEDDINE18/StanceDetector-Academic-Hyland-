import os
import fitz  # PyMuPDF

class PDFExtractor:
    def __init__(self, directory=".", output_dir="extracted_txt"):
        """
        Initialise the PDF extractor with a directory to scan and output folder.
        """
        self.directory = directory
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ---- STATIC METHODS (class-level, no instance needed) ----
    @staticmethod
    def list_pdfs(directory="."):
        """
        List all PDF files in the given directory.
        Usage: PDFExtractor.list_pdfs()
        """
        return [f for f in os.listdir(directory) if f.lower().endswith(".pdf")]

    @staticmethod
    def extract_text(pdf_file, output_dir="extracted_txt"):
        """
        Extract all text from a single PDF and save it as a .txt file.
        Usage: PDFExtractor.extract_text("file.pdf")
        """
        os.makedirs(output_dir, exist_ok=True)
        doc = fitz.open(pdf_file)

        output_path = os.path.join(
            output_dir,
            os.path.basename(pdf_file).replace(".pdf", ".txt")
        )

        with open(output_path, "w", encoding="utf-8") as f:
            for page_num in range(len(doc)):
                text = doc[page_num].get_text("text")
                f.write(f"\n--- Page {page_num+1} ---\n")
                f.write(text)
                f.write("\n")

        return output_path

    # ---- INSTANCE METHOD ----
    def extract_multiple(self, pdf_list=None):
        """
        Extract text from multiple PDFs in this instance's directory.
        If no list is given, all PDFs in directory are processed.
        """
        if pdf_list is None:
            pdf_list = PDFExtractor.list_pdfs(self.directory)

        results = []
        for pdf in pdf_list:
            pdf_path = os.path.join(self.directory, pdf)
            out = PDFExtractor.extract_text(pdf_path, self.output_dir)
            results.append(out)
        return results
    
