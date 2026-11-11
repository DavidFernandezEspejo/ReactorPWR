from pathlib import Path

from pypdf import PdfReader


def main() -> None:
    pdf_candidates = sorted(Path("docs").glob("*.pdf"))
    if not pdf_candidates:
        raise SystemExit("No se encontro ningun PDF en docs/")

    pdf_path = pdf_candidates[0]
    reader = PdfReader(str(pdf_path))
    first_page_preview = (reader.pages[0].extract_text() or "").strip()[:600]

    print(f"Archivo: {pdf_path}")
    print(f"Paginas: {len(reader.pages)}")
    print("--- Extracto primera pagina ---")
    print(first_page_preview)


if __name__ == "__main__":
    main()

