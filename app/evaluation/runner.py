"""
Evaluation runner — executes the golden set against the live system.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from app.evaluation.golden_set import get_golden_set
from app.models.state import AgentState
from app.graph.workflow import build_graph


def _to_dict(obj):
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return {}


class EvalRunner:
    def __init__(self):
        print("🔧 Building workflow graph...")
        self.workflow = build_graph()
        self.results: List[Dict] = []

    def run_single(self, case: Dict) -> Dict:
        """Run one test case through the system."""
        start = time.time()

        state = AgentState(
            session_id=f"eval-{case['id']}",
            user_message=case["question"],
        )

        try:
            result = self.workflow.invoke(state)
            result_dict = _to_dict(result)
            elapsed = time.time() - start

            answer = result_dict.get("answer", "")
            actual_intent = result_dict.get("intent", "unknown")
            actual_domain = result_dict.get("domain", "unknown")
            retrieved = result_dict.get("retrieved_chunks", [])
            session_data = result_dict.get("session", {})

            # Build retrieved contexts list (for RAGAS)
            contexts = [
                c.get("content", "") if isinstance(c, dict) else c.content
                for c in retrieved
            ]

            # Score components
            intent_match = (
                "expected_intent" not in case
                or actual_intent == case["expected_intent"]
            )
            domain_match = (
                "expected_domain" not in case
                or actual_domain == case["expected_domain"]
            )

            # Must-contain check (lowercase substring match — ANY token)
            must_contain_pass = True
            if "must_contain" in case:
                must_contain_pass = any(
                    token.lower() in answer.lower()
                    for token in case["must_contain"]
                )

            # Block check (for guardrail tests)
            blocked_correctly = True
            if case.get("should_block"):
                blocked_correctly = session_data.get("input_blocked", False)

            # Escalation check
            escalated_correctly = True
            if case.get("should_escalate"):
                escalated_correctly = (
                    result_dict.get("needs_escalation", False)
                    or "ticket" in answer.lower()
                )

            passed = (
                intent_match
                and must_contain_pass
                and blocked_correctly
                and escalated_correctly
            )

            return {
                "id": case["id"],
                "category": case.get("category", "n/a"),
                "question": case["question"],
                "expected_answer": case.get("expected_answer", ""),
                "actual_answer": answer,
                "expected_intent": case.get("expected_intent"),
                "actual_intent": actual_intent,
                "expected_domain": case.get("expected_domain"),
                "actual_domain": actual_domain,
                "contexts": contexts,
                "must_contain": case.get("must_contain", []),
                "must_contain_pass": must_contain_pass,
                "intent_match": intent_match,
                "domain_match": domain_match,
                "blocked_correctly": blocked_correctly,
                "escalated_correctly": escalated_correctly,
                "passed": passed,
                "elapsed_sec": round(elapsed, 2),
                "groundedness": session_data.get("groundedness"),
                "error": None,
            }

        except Exception as e:
            return {
                "id": case["id"],
                "category": case.get("category", "n/a"),
                "question": case["question"],
                "actual_answer": "",
                "contexts": [],
                "passed": False,
                "elapsed_sec": round(time.time() - start, 2),
                "error": str(e),
            }

    def run_all(self) -> List[Dict]:
        cases = get_golden_set()
        print(f"\n🚀 Running {len(cases)} test cases...\n")

        for i, case in enumerate(cases, 1):
            print(f"  [{i:2d}/{len(cases)}] {case['id']}: {case['question'][:60]}...", end=" ")
            result = self.run_single(case)
            self.results.append(result)
            status = "✅" if result["passed"] else "❌"
            print(f"{status} ({result['elapsed_sec']}s)")

        return self.results

    def summary(self) -> Dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        errors = sum(1 for r in self.results if r.get("error"))

        # Per-category breakdown
        from collections import defaultdict
        cat_stats = defaultdict(lambda: {"total": 0, "passed": 0})
        for r in self.results:
            cat = r["category"]
            cat_stats[cat]["total"] += 1
            if r["passed"]:
                cat_stats[cat]["passed"] += 1

        avg_latency = round(
            sum(r["elapsed_sec"] for r in self.results) / max(total, 1),
            2,
        )

        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "errors": errors,
            "pass_rate": round(passed / max(total, 1) * 100, 1),
            "avg_latency_sec": avg_latency,
            "by_category": dict(cat_stats),
        }

    def save_results(self, output_dir: str = "data/eval_results"):
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON
        json_path = out_dir / f"eval_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": timestamp,
                "summary": self.summary(),
                "results": self.results,
            }, f, indent=2)
        print(f"\n💾 Results saved: {json_path}")
        return json_path


def main():
    print("=" * 60)
    print("🧪 SmartHelpDesk AI — Evaluation Suite")
    print("=" * 60)

    runner = EvalRunner()
    runner.run_all()

    summary = runner.summary()
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"  Total:        {summary['total']}")
    print(f"  ✅ Passed:    {summary['passed']}")
    print(f"  ❌ Failed:    {summary['failed']}")
    print(f"  ⚠️  Errors:   {summary['errors']}")
    print(f"  Pass rate:    {summary['pass_rate']}%")
    print(f"  Avg latency:  {summary['avg_latency_sec']}s")

    print("\n📂 By category:")
    for cat, stats in summary["by_category"].items():
        rate = round(stats["passed"] / max(stats["total"], 1) * 100, 0)
        print(f"  • {cat:15s} {stats['passed']}/{stats['total']}  ({rate:.0f}%)")

    runner.save_results()
    print("\n✅ Evaluation complete!")
    return runner


if __name__ == "__main__":
    main()