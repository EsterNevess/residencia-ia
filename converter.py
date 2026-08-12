import io
import os
from pathlib import Path

os.environ["TORCHDYNAMO_DISABLE"] = "1"

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption

print("Iniciando o Docling (Modo Leve)...")

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(backend=PyPdfiumDocumentBackend)
    }
)

pasta_pdfs = Path("AULA_02") / "PDFS"
pasta_markdown = Path("AULA_02") / "MARKDOWN"

pasta_markdown.mkdir(parents=True, exist_ok=True)

arquivos_pdf = list(pasta_pdfs.glob("*.pdf"))
print(f"Encontrados {len(arquivos_pdf)} PDFs para converter.\n")

for pdf in arquivos_pdf:
  print(f"⌛ Processando {pdf.name}...")
  try:
    pdf_bytes = pdf.read_bytes()
    doc_stream = DocumentStream(name=pdf.name, stream=io.BytesIO(pdf_bytes))

    result = converter.convert(doc_stream)

    md_path = pasta_markdown / f"{pdf.stem}.md"

    with open(md_path, "w", encoding="utf-8") as f:
      f.write(result.document.export_to_markdown())

    print(f"✅ Gerado com sucesso: {md_path.name}\n")
  except Exception as e:
    print(f"❌ Erro em {pdf.name}: {e}\n")

print("🎉 Todos os arquivos foram processados!")