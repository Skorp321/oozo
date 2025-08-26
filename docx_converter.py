import json 
import logging
from pathlib import Path
import yaml

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

DOC_SOURCE = "docs/42.-trudovoj-dogovor-master-apparatnogo-massazha.docx"

doc = DocumentConverter().convert(source=DOC_SOURCE).document
chunker = HybridChunker(
    chunk_size=1000,
    chunk_overlap=100,    
)

chunks = chunker.chunk(dl_doc=doc)

for i, chunk in enumerate(chunks):
    print(f"=== {i} ===")
    print(f"chunk.text: \n{f'{chunk.text}'!r}")
    
    enriched_text = chunker.contextualize(chunk=chunk)  
    #print(f"Chunker.contextualize(chunk):\n{f'{enriched_text}...'!r}")
    print("-" * 100)