"""
Production-grade batched ingestion for SmartHelpDesk AI.
Run: python -m app.services.kb_ingest
"""

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from app.core.config import settings
from app.services.dataset_loader import build_full_kb, save_processed

BATCH_SIZE = 100  # Embed in batches of 100 docs


def build_documents(entries: list):
    docs = []
    for e in entries:
        content = f"Question: {e['question']}\nAnswer: {e['answer']}"
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "id": e["id"],
                    "category": e["category"],
                    "domain": e["domain"],
                    "source": e.get("source", "")
                }
            )
        )
    return docs


def ingest_collection(docs, collection_name):
    embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key,
                                   model="text-embedding-3-small")

    # Wipe existing
    try:
        old = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=settings.chroma_persist_dir,
        )
        old.delete_collection()
        print(f"   🧹 Cleared collection: {collection_name}")
    except Exception as e:
        print(f"   ℹ️  No existing collection ({e})")

    # Create fresh vector store
    vs = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )

    total = len(docs)
    for i in range(0, total, BATCH_SIZE):
        batch = docs[i:i + BATCH_SIZE]
        vs.add_documents(batch)
        print(f"   📦 Batch {i // BATCH_SIZE + 1}: ingested {min(i + BATCH_SIZE, total)}/{total}")

    print(f"   ✅ {collection_name}: {total} docs ingested")


# ============================================================
# ✅ SELF-HEALING STARTUP CHECK
# ============================================================
# Whether a given container/image happens to already have an
# ingested data/chroma or not (baked into the image, copied in,
# a fresh build, a stale volume, etc.) should not matter. On
# startup we check whether hr_docs/it_docs actually have data,
# and auto-ingest only if they don't. Safe to call every startup —
# costs nothing (no embedding calls) once the KB is populated.
# ============================================================

def is_collection_populated(collection_name: str) -> bool:
    """Check whether a Chroma collection already has documents."""
    try:
        embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model="text-embedding-3-small",
        )
        vs = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=settings.chroma_persist_dir,
        )
        return vs._collection.count() > 0
    except Exception as e:
        print(f"[kb_ingest] Could not check collection '{collection_name}': {e}")
        return False


def ensure_kb_ingested():
    """
    Idempotent startup check. If hr_docs and/or it_docs are empty
    (fresh container, image without baked-in KB, wiped volume,
    etc.), ingest automatically so the app is never silently
    missing its knowledge base. Does nothing if data is already
    present.
    """
    needs_hr = not is_collection_populated("hr_docs")
    needs_it = not is_collection_populated("it_docs")

    if not needs_hr and not needs_it:
        print("[kb_ingest] ✅ KB already populated — skipping auto-ingest.")
        return

    print("[kb_ingest] ⚠️  KB missing or incomplete — running ingestion automatically...")
    kb = build_full_kb()
    save_processed(kb)

    if needs_hr:
        print("[kb_ingest] 📘 Ingesting HR collection...")
        ingest_collection(build_documents(kb["hr"]), "hr_docs")

    if needs_it:
        print("[kb_ingest] 💻 Ingesting IT collection...")
        ingest_collection(build_documents(kb["it"]), "it_docs")

    print("[kb_ingest] ✅ Auto-ingest complete.")


def main():
    print("=" * 60)
    print("🚀 SmartHelpDesk AI — Production Ingestion Pipeline")
    print("=" * 60)

    print("\n[Step 1/3] Building normalized KB...")
    kb = build_full_kb()

    print("\n[Step 2/3] Saving processed JSONL...")
    save_processed(kb)

    print("\n[Step 3/3] Embedding + storing in ChromaDB...")
    print("\n📘 HR ingestion...")
    ingest_collection(build_documents(kb["hr"]), "hr_docs")

    print("\n💻 IT ingestion...")
    ingest_collection(build_documents(kb["it"]), "it_docs")

    print("\n" + "=" * 60)
    print(f"✅ COMPLETE! HR={len(kb['hr'])}, IT={len(kb['it'])}")
    print(f"📂 Chroma persist: {settings.chroma_persist_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
