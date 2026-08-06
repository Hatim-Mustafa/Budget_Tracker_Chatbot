# src/ingest.py
import os
import psycopg
from markitdown import MarkItDown
from chonkie import TokenChunker
from openai import OpenAI
from pydantic_ai.providers.openai import OpenAIProvider


base_url: str = "https://opencode.ai/zen/v1"
# Initialize clients
client = OpenAI(
    api_key=os.getenv("OPENCODE_API_KEY"), 
    base_url=base_url,
    )
mid = MarkItDown()
db_conn = psycopg.connect(os.getenv("DATABASE_URL")) # e.g., postgresql://...

# 1. Parse any file to clean markdown string
result = mid.convert("data/handbook.pdf")
markdown_text = result.text_content

file_path = "data/handbook.pdf"
with open(file_path, "rb") as f:
    file_bytes = f.read()

# 2. Chunk semantically using Chonkie (Token Based)
# Chonkie splits cleanly on token limits to prevent text truncation
chunker = TokenChunker(tokenizer="gpt-4o", chunk_size=400, chunk_overlap=50)
chunks = chunker.chunk(markdown_text)

# 3. Generate embeddings and save to Postgres
with db_conn.cursor() as cur:

    cur.execute(
        """
        INSERT INTO source_documents (file_name, file_type, raw_binary)
        VALUES (%s, %s, %s) RETURNING id;
        """,
        ("handbook.pdf", "application/pdf", psycopg.Binary(file_bytes))
    )
    document_id = cur.fetchone()[0]

    for idx, chunk in enumerate(chunks):
        # Generate embedding vector
        response = client.embeddings.create(
            input=[chunk.text],
            model="text-embedding-3-small"
        )
        vector = response.data[0].embedding
        
        # Insert into pgvector
        cur.execute(
        """
        INSERT INTO document_embeddings (document_id, chunk_index, content, embedding)
        VALUES (%s, %s, %s, %s);
        """,
        (document_id, idx, chunk.text, vector)
    )
    db_conn.commit()
print("Ingestion complete!")
