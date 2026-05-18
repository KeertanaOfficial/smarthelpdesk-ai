# app/services/retrieval_service.py

from typing import List
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from app.core.config import settings
from app.models.state import RetrievedChunk

# =====================================================
# ✅ GLOBAL EMBEDDINGS (singleton)
# =====================================================
_embeddings = None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model="text-embedding-3-small",
        )
    return _embeddings


# =====================================================
# ✅ VECTOR STORE
# =====================================================
def get_vectorstore(collection_name: str):
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
    )


# =====================================================
# ✅ MAIN RETRIEVAL
# =====================================================
def retrieve_docs(query: str, domain: str, k: int = 4) -> List[RetrievedChunk]:
    collection = "hr_docs" if domain == "hr" else "it_docs"
    vs = get_vectorstore(collection)

    docs = vs.similarity_search_with_score(query, k=k)

    results = []
    for d, score in docs:
        results.append(
            RetrievedChunk(
                content=d.page_content,
                source=d.metadata.get("source", "unknown"),
                score=float(score),
                metadata=d.metadata,
            )
        )

    # ✅ DEBUG (VERY IMPORTANT)
    print("\n======= RETRIEVAL DEBUG =======")
    print(f"Query: {query}")
    print(f"Domain: {domain}")
    print(f"Results: {len(results)}")

    for r in results:
        print(f"Score: {r.score:.4f}")
        print(r.content[:120])
        print("-" * 40)

    return results


# =====================================================
# ✅ COSINE SIMILARITY-BASED RELATED QUESTIONS
# =====================================================
def get_related_questions(query: str, domain: str, k: int = 3):
    collection = "hr_docs" if domain == "hr" else "it_docs"
    vs = get_vectorstore(collection)

    docs = vs.similarity_search(query, k=k)

    questions = []
    for d in docs:
        text = d.page_content

        if "Question:" in text:
            try:
                q = text.split("Question:")[1].split("\n")[0].strip()
                questions.append(q)
            except:
                continue

    # remove duplicates + limit
    return list(dict.fromkeys(questions))[:k]