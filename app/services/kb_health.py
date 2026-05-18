"""
Knowledge Base health check — shows KB stats on startup.
"""

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from app.core.config import settings


def _make_embeddings():
    """Create embeddings instance (matches ingestion config)."""
    return OpenAIEmbeddings(
        api_key=settings.openai_api_key,
        model="text-embedding-3-small",
    )


def check_kb_health() -> dict:
    """Check if KB collections exist and return counts."""
    stats = {}

    # Build embeddings once, outside the loop
    try:
        embeddings = _make_embeddings()
    except Exception as e:
        return {
            "hr_docs": f"EMBEDDINGS_ERROR: {e}",
            "it_docs": f"EMBEDDINGS_ERROR: {e}",
        }

    for collection in ["hr_docs", "it_docs"]:
        try:
            vs = Chroma(
                collection_name=collection,
                embedding_function=embeddings,
                persist_directory=settings.chroma_persist_dir,
            )
            count = vs._collection.count()
            stats[collection] = count
        except Exception as e:
            stats[collection] = f"ERROR: {e}"

    return stats


def print_kb_health():
    print("\n" + "=" * 50)
    print("📊 Knowledge Base Health Check")
    print("=" * 50)

    stats = check_kb_health()

    for name, count in stats.items():
        if isinstance(count, int):
            status = "✅" if count > 0 else "⚠️ EMPTY"
            print(f"   {status} {name}: {count} documents")
        else:
            print(f"   ❌ {name}: {count}")

    total = sum(c for c in stats.values() if isinstance(c, int))
    if total == 0:
        print("\n⚠️  KB is empty or unreachable!")
        print("   Run: python -m app.services.kb_ingest")
    else:
        print(f"\n✅ Total: {total} documents ready for retrieval")

    print("=" * 50 + "\n")


if __name__ == "__main__":
    print_kb_health()