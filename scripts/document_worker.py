"""Optional PDF extractor, isolated from the stdlib application process."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import sys
import time


def convert(path, engine):
    started = time.perf_counter()
    from pypdf import PdfReader
    reader = PdfReader(path)
    if reader.is_encrypted and not reader.decrypt(''):
        raise ValueError('PDF cifrado: aporta una copia legible.')
    if not 1 <= len(reader.pages) <= 300:
        raise ValueError('El límite es de 300 páginas.')
    metadata = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
    tables = 0
    if engine == 'pypdf':
        pages = [{'physical_page': i + 1, 'text': page.extract_text() or ''}
                 for i, page in enumerate(reader.pages)]
        version = importlib.metadata.version('pypdf')
    else:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, NativePdfPipelineOptions
        from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
        if engine == 'docling-native':
            from docling.pipeline.native_pdf_pipeline import NativePdfPipeline
            options = NativePdfPipelineOptions(document_timeout=600,
                        accelerator_options=AcceleratorOptions(num_threads=4,device=AcceleratorDevice.CPU))
            pdf_option = PdfFormatOption(pipeline_cls=NativePdfPipeline, pipeline_options=options)
        else:
            options = PdfPipelineOptions(do_ocr=False, do_table_structure=True,
                        document_timeout=600,
                        accelerator_options=AcceleratorOptions(num_threads=4, device=AcceleratorDevice.CPU))
            pdf_option = PdfFormatOption(pipeline_options=options)
        converter = DocumentConverter(format_options={InputFormat.PDF: pdf_option})
        result = converter.convert(path, max_num_pages=300, max_file_size=50 * 1024 * 1024)
        if str(result.status.value) != 'success':
            raise ValueError('Conversión Docling incompleta: ' + str(result.status))
        doc = result.document
        pages = [{'physical_page': i, 'text': doc.export_to_markdown(page_no=i)}
                 for i in sorted(doc.pages)]
        tables = len(doc.tables)
        version = importlib.metadata.version('docling')
    if len(pages) != len(reader.pages):
        raise ValueError('La conversión omitió páginas.')
    peak = None
    try:
        import psutil
        info = psutil.Process().memory_info()
        peak = getattr(info, 'peak_wset', None)
    except ImportError:
        pass
    return {'engine': engine, 'version': version, 'ocr': False, 'pages': pages,
            'metadata_declared_in_pdf': metadata, 'tables_detected': tables,
            'seconds': round(time.perf_counter() - started, 3), 'peak_rss_bytes': peak,
            'page_labels_declared': reader.page_labels}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf'); parser.add_argument('output')
    parser.add_argument('--engine', choices=['pypdf', 'docling-native', 'docling-standard'], default='pypdf')
    args = parser.parse_args()
    try:
        data = convert(Path(args.pdf), args.engine)
        Path(args.output).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
