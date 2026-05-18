"""
Master evaluation script — runs everything end-to-end.

Usage:
    python scripts/run_eval.py              # Standard eval
    python scripts/run_eval.py --with-ragas # Include RAGAS (costs ~$0.20)
"""

import sys
from pathlib import Path

# Make project root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.evaluation.runner import EvalRunner
from app.evaluation.metrics import run_ragas_eval
from app.evaluation.report import generate_html_report


def main():
    use_ragas = "--with-ragas" in sys.argv

    print("=" * 60)
    print("🧪 SmartDesk AI — Full Evaluation Pipeline")
    print("=" * 60)

    # Step 1: Run golden set
    runner = EvalRunner()
    runner.run_all()

    summary = runner.summary()
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"  Total:       {summary['total']}")
    print(f"  ✅ Passed:   {summary['passed']}")
    print(f"  ❌ Failed:   {summary['failed']}")
    print(f"  Pass rate:   {summary['pass_rate']}%")
    print(f"  Avg latency: {summary['avg_latency_sec']}s")

    json_path = runner.save_results()

    # Step 2: RAGAS (optional)
    ragas_scores = None
    if use_ragas:
        ragas_scores = run_ragas_eval(runner.results)
        if "error" in ragas_scores:
            print(f"\n⚠️  RAGAS: {ragas_scores['error']}")
        else:
            print("\n🔬 RAGAS Metrics:")
            print(f"  • Faithfulness:       {ragas_scores['faithfulness']}")
            print(f"  • Answer Relevance:   {ragas_scores['answer_relevancy']}")
            print(f"  • Context Precision:  {ragas_scores['context_precision']}")

    # Step 3: HTML report
    html_path = generate_html_report(str(json_path), ragas_scores=ragas_scores)
    print(f"\n📂 Open report: {html_path}")
    print("\n✅ Evaluation complete!")


if __name__ == "__main__":
    main()