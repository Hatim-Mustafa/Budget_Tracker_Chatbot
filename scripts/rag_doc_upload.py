# src/ingest.py
import os
from pathlib import Path

import psycopg
from chonkie import TokenChunker
from google import genai
from google.genai import types
from markitdown import MarkItDown
from openai import OpenAI

base_url: str = "https://opencode.ai/zen/v1"
# Initialize clients
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
mid = MarkItDown()
# psycopg.connect() only understands a libpq URI or conninfo string, not a
# SQLAlchemy URL — strip the "+psycopg" dialect marker first.
db_conn = psycopg.connect(
    os.getenv("DATABASE_URL").replace("+psycopg", "")
)  # e.g., postgresql://...

# Resolve the project data folder relative to this script, so the script works
# from any working directory.
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# 1. Parse any file to clean markdown string
file_path = DATA_DIR / "doc3.pdf"
result = mid.convert(str(file_path))
markdown_text = result.text_content

with open(file_path, "rb") as f:
    file_bytes = f.read()

# 2. Chunk semantically using Chonkie (Token Based)
# Chonkie splits cleanly on token limits to prevent text truncation
chunker = TokenChunker(tokenizer="cl100k_base", chunk_size=400, chunk_overlap=50)
chunks = chunker.chunk(markdown_text)

# 3. Generate embeddings and save to Postgres
with db_conn.cursor() as cur:
    cur.execute(
        """
        INSERT INTO source_documents (file_name, file_type, raw_binary)
        VALUES (%s, %s, %s) RETURNING id;
        """,
        ("doc3.pdf", "application/pdf", psycopg.Binary(file_bytes)),
    )
    document_id = cur.fetchone()[0]

    for idx, chunk in enumerate(chunks):
        # Generate embedding vector
        response = client.models.embed_content(
            # FIX: Change from text-embedding-004 to gemini-embedding-001
            model="gemini-embedding-001",
            contents=chunk.text,
            config=types.EmbedContentConfig(
                # Set task type to optimize it for document vector search
                task_type="RETRIEVAL_DOCUMENT",
                # Truncate dimensionality to clean 768 dimensions
                output_dimensionality=768,
            ),
        )
        vector = response.embeddings[0].values

        # Insert into pgvector
        cur.execute(
            """
        INSERT INTO document_embeddings (document_id, chunk_index, content, embedding)
        VALUES (%s, %s, %s, %s);
        """,
            (document_id, idx, chunk.text, vector),
        )
    db_conn.commit()
print("Ingestion complete!")
