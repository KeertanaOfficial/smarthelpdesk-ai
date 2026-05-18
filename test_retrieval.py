from app.services.retrieval_service import retrieve_docs

print("\n--- IT Test ---")
results = retrieve_docs("how do I reset my password", domain="it")
for r in results:
    print(f"[{r.score:.2f}] {r.source}: {r.content[:80]}...")

print("\n--- HR Test ---")
results = retrieve_docs("how many leave days do I get", domain="hr")
for r in results:
    print(f"[{r.score:.2f}] {r.source}: {r.content[:80]}...")