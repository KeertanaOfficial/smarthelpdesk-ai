"""
RAGAS-based metrics for RAG quality.
- Faithfulness: Are claims in answer supported by context?
- Answer Relevance: Does answer address the question?
- Context Precision: Are retrieved docs relevant?
"""

import os
from typing import List, Dict
from app.core.config import settings


def run_ragas_eval(results: List[Dict]) -> Dict:
    """
    Run RAGAS metrics on eval results.
    Only runs on KB-query results with retrieved contexts.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
        )
    except ImportError as e:
        return {"error": f"RAGAS not installed: {e}"}

    # Filter to KB queries that have contexts
    eligible = [
        r for r in results
        if r.get("contexts")
        and r.get("expected_intent") == "kb_query"
        and not r.get("error")
    ]

    if not eligible:
        return {"error": "No eligible results for RAGAS evaluation."}

    # Build dataset
    data = {
        "question": [r["question"] for r in eligible],
        "answer": [r["actual_answer"] for r in eligible],
        "contexts": [r["contexts"] for r in eligible],
        "ground_truth": [r.get("expected_answer", "") for r in eligible],
    }
    dataset = Dataset.from_dict(data)

    # Set API key for RAGAS
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key

    print(f"\n🔬 Running RAGAS on {len(eligible)} eligible results...")
    print("   (This may take 1-3 minutes — each metric calls the LLM)")

    try:
        scores = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision],
        )

        # Aggregate scores
        df = scores.to_pandas()
        aggregated = {
            "faithfulness": round(float(df["faithfulness"].mean()), 3),
            "answer_relevancy": round(float(df["answer_relevancy"].mean()), 3),
            "context_precision": round(float(df["context_precision"].mean()), 3),
            "evaluated_count": len(eligible),
        }
        return aggregated

    except Exception as e:
        return {"error": f"RAGAS run failed: {e}"}


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.evaluation.metrics <eval_results.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    scores = run_ragas_eval(data["results"])
    print("\n📊 RAGAS Scores:")
    print(json.dumps(scores, indent=2))