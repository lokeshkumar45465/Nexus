
import hashlib
from pathlib import Path

import chromadb
import ollama
import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DOCUMENTS_DIR = BASE_DIR / "documents"
CHROMA_DIR = BASE_DIR / "chroma_db"

CHAT_MODEL = "llama3.2"
EMBEDDING_MODEL = "nomic-embed-text"

COLLECTION_NAME = "edgesight_documents"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

DOCUMENTS_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)


# --------------------------------------------------
# 2. Connect to ChromaDB
# --------------------------------------------------

client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"description": "EdgeSight technical documents"}
)


# --------------------------------------------------
# 3. Read PDF, TXT and Markdown documents
# --------------------------------------------------

def read_document(file_path):
    """Extract text from supported document formats."""

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            if text.strip():
                pages.append({
                    "text": text,
                    "page": page_number
                })

        return pages

    if extension in [".txt", ".md"]:
        text = file_path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        return [{
            "text": text,
            "page": None
        }]

    return []


# --------------------------------------------------
# 4. Split document text into smaller chunks
# --------------------------------------------------

def split_text(text):
    """Split long text into overlapping chunks."""

    text = " ".join(text.split())

    chunks = []

    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


# --------------------------------------------------
# 5. Create embeddings using Ollama
# --------------------------------------------------

def create_embeddings(texts):
    """Convert text into numerical vectors."""

    response = ollama.embed(
        model=EMBEDDING_MODEL,
        input=texts
    )

    return response["embeddings"]


# --------------------------------------------------
# 6. Index documents in ChromaDB
# --------------------------------------------------

def index_documents():
    """Read documents, create embeddings and store them."""

    files = []

    for extension in ["*.pdf", "*.txt", "*.md"]:
        files.extend(DOCUMENTS_DIR.glob(extension))

    if not files:
        return {
            "success": False,
            "message": (
                "No PDF, TXT or Markdown files found "
                "inside the documents folder."
            ),
            "chunks": 0,
            "files": 0
        }

    total_chunks = 0

    for file_path in files:
        collection.delete(
            where={"source": file_path.name}
       )
        pages = read_document(file_path)

        documents = []
        metadatas = []
        ids = []

        for page_data in pages:

            chunks = split_text(page_data["text"])

            for chunk_number, chunk in enumerate(chunks):

                identity = (
                    f"{file_path.name}-"
                    f"{page_data['page']}-"
                    f"{chunk_number}-"
                    f"{chunk}"
                )

                chunk_id = hashlib.sha256(
                    identity.encode("utf-8")
                ).hexdigest()

                metadata = {
                    "source": file_path.name,
                    "chunk": chunk_number
                }

                if page_data["page"] is not None:
                    metadata["page"] = page_data["page"]

                documents.append(chunk)
                metadatas.append(metadata)
                ids.append(chunk_id)

        if not documents:
            continue

        # Generate embeddings in small batches.
        for start in range(0, len(documents), 32):

            end = start + 32

            batch_documents = documents[start:end]
            batch_metadata = metadatas[start:end]
            batch_ids = ids[start:end]

            embeddings = create_embeddings(batch_documents)

            collection.upsert(
                ids=batch_ids,
                documents=batch_documents,
                embeddings=embeddings,
                metadatas=batch_metadata
            )

            total_chunks += len(batch_documents)

    return {
        "success": True,
        "message": "Document indexing completed.",
        "chunks": total_chunks,
        "files": len(files)
    }


# --------------------------------------------------
# 7. Retrieve relevant document information
# --------------------------------------------------

def retrieve_documents(question, top_k=4):
    """Find document chunks relevant to the question."""

    if collection.count() == 0:
        return []

    question_embedding = create_embeddings([question])

    results = collection.query(
        query_embeddings=question_embedding,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    retrieved = []

    for document, metadata in zip(
        results["documents"][0],
        results["metadatas"][0]
    ):
        retrieved.append({
            "text": document,
            "source": metadata.get("source", "Unknown"),
            "page": metadata.get("page")
        })

    return retrieved


# --------------------------------------------------
# 8. Prepare IoT dataset analytics using Pandas
# --------------------------------------------------

def build_dataset_context(df):
    """Calculate useful statistics from the IoT dataset."""

    if df is None or df.empty:
        return "No IoT dataset records are currently available."

    details = []

    details.append(f"Total records: {len(df)}")

    if "asset_id" in df.columns:
        details.append(
            f"Unique assets: {df['asset_id'].nunique()}"
        )

    if "asset_type" in df.columns:
        counts = df["asset_type"].value_counts().to_dict()

        details.append(
            f"Records by equipment type: {counts}"
        )

    # Health score
    if "ai_health_index_score" in df.columns:
        values = pd.to_numeric(
            df["ai_health_index_score"],
            errors="coerce"
        )

        if values.notna().any():
            details.append(
                f"Average health score: {values.mean():.2f}"
            )

            details.append(
                f"Lowest health score: {values.min():.2f}"
            )

            details.append(
                f"Highest health score: {values.max():.2f}"
            )

    # Temperature
    if "bearing_temp_c" in df.columns:
        values = pd.to_numeric(
            df["bearing_temp_c"],
            errors="coerce"
        )

        if values.notna().any():
            details.append(
                f"Average bearing temperature: "
                f"{values.mean():.2f} °C"
            )

            details.append(
                f"Maximum bearing temperature: "
                f"{values.max():.2f} °C"
            )

            if "asset_id" in df.columns:
                index = values.idxmax()

                details.append(
                    f"Asset with maximum bearing temperature: "
                    f"{df.loc[index, 'asset_id']}"
                )

    # Vibration
    if "vibration_rms_mm_s" in df.columns:
        values = pd.to_numeric(
            df["vibration_rms_mm_s"],
            errors="coerce"
        )

        if values.notna().any():
            details.append(
                f"Average vibration: {values.mean():.2f} mm/s"
            )

            details.append(
                f"Maximum vibration: {values.max():.2f} mm/s"
            )

            if "asset_id" in df.columns:
                index = values.idxmax()

                details.append(
                    f"Asset with maximum vibration: "
                    f"{df.loc[index, 'asset_id']}"
                )

    # Failure and maintenance counts
    count_columns = [
        "prior_failures_last_12m",
        "num_sensor_alerts_last_7d",
        "scheduled_pm_due_within_7d",
        "unscheduled_failure_within_7d"
    ]

    for column in count_columns:
        if column in df.columns:

            values = df[column]

            numeric_values = pd.to_numeric(
                values,
                errors="coerce"
            )

            if numeric_values.notna().any():
                total = numeric_values.fillna(0).sum()

            else:
                normalized = (
                    values.astype(str)
                    .str.strip()
                    .str.lower()
                )

                total = normalized.isin(
                    ["true", "yes", "1"]
                ).sum()

            details.append(
                f"{column}: {total}"
            )

    return "\n".join(details)


# --------------------------------------------------
# 9. Generate the final RAG answer
# --------------------------------------------------

def generate_rag_answer(question, df, chat_history=None):
    """Combine document retrieval, Pandas and Ollama."""

    retrieved_docs = retrieve_documents(question)

    if retrieved_docs:
        document_context = "\n\n".join(
            [
                (
                    f"Source: {item['source']}, "
                    f"Page: {item['page']}\n"
                    f"{item['text']}"
                )
                for item in retrieved_docs
            ]
        )
    else:
        document_context = (
            "No relevant document information was found. "
            "Do not invent information from technical manuals."
        )

    dataset_context = build_dataset_context(df)

    system_prompt = f"""
You are EdgeSight Query Nexus, an IoT technical assistant.

Answer the user's question using the provided information.

DOCUMENT INFORMATION:
{document_context}

IOT DATASET ANALYTICS:
{dataset_context}

RULES:
1. Use document information for technical manual questions.
2. Use dataset analytics for IoT statistics and measurements.
3. Clearly distinguish document information from dataset results.
4. Never invent values, measurements, or technical specifications.
5. If the information is unavailable, say so.
6. Explain the answer in simple language.
7. Mention document filenames and page numbers when available.
8. Do not claim that a document supports something it does not say.
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # Keep only a small amount of recent conversation history.
    if chat_history:
        for message in chat_history[-4:]:
            if message["role"] in ["user", "assistant"]:
                messages.append({
                    "role": message["role"],
                    "content": message["content"]
                })

    messages.append({
        "role": "user",
        "content": question
    })

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=messages,
        options={
            "temperature": 0.2
        }
    )

    return response["message"]["content"]


# --------------------------------------------------
# 10. Get knowledge base information
# --------------------------------------------------

def get_knowledge_base_count():
    """Return the number of indexed document chunks."""

    return collection.count()
