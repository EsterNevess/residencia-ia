import os
import io
from pathlib import Path

os.environ["TORCHDYNAMO_DISABLE"] = "1"

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat, DocumentStream
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

print("Iniciando o Docling (Modo Leve)...")

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            backend=PyPdfiumDocumentBackend
        )
    }
)

pasta = Path("aula_2")

for pdf in pasta.glob("*.pdf"):
    print(f"⌛ Processando {pdf.name}...")
    try:

        pdf_bytes = pdf.read_bytes()
        doc_stream = DocumentStream(
            name=pdf.name,
            stream=io.BytesIO(pdf_bytes)
        )
        
        result = converter.convert(doc_stream)
        md_path = pdf.with_suffix(".md")
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result.document.export_to_markdown())
            
        print(f"✅ Gerado com sucesso: {md_path.name}\n")
    except Exception as e:
        print(f"❌ Erro em {pdf.name}: {e}\n")

print("🎉 Todos os arquivos foram processados!")