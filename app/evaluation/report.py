"""
Generate human-readable HTML/Markdown reports from eval results.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>SmartDesk AI - Evaluation Report</title>
  <style>
    body {{ font-family: -apple-system, Segoe UI, sans-serif; max-width: 1200px; margin: 40px auto; padding: 20px; color: #333; }}
    h1 {{ border-bottom: 3px solid #4a90e2; padding-bottom: 10px; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0; }}
    .card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #4a90e2; }}
    .card .num {{ font-size: 32px; font-weight: bold; color: #4a90e2; }}
    .card .label {{ color: #666; font-size: 14px; }}
    .pass {{ color: #28a745; }}
    .fail {{ color: #dc3545; }}
    .ragas {{ background: #e7f3ff; padding: 16px; border-radius: 8px; margin: 20px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
    th {{ background: #4a90e2; color: white; }}
    tr:hover {{ background: #f5f5f5; }}
    .status {{ font-weight: bold; }}
    details {{ margin: 8px 0; }}
    summary {{ cursor: pointer; padding: 6px; background: #f0f0f0; border-radius: 4px; }}
    pre {{ background: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>🧪 SmartDesk AI — Evaluation Report</h1>
  <p><strong>Generated:</strong> {timestamp}</p>

  <h2>📊 Summary</h2>
  <div class="summary">
    <div class="card">
      <div class="num">{total}</div>
      <div class="label">Total Tests</div>
    </div>
    <div class="card">
      <div class="num pass">{passed}</div>
      <div class="label">Passed</div>
    </div>
    <div class="card">
      <div class="num fail">{failed}</div>
      <div class="label">Failed</div>
    </div>
    <div class="card">
      <div class="num">{pass_rate}%</div>
      <div class="label">Pass Rate</div>
    </div>
  </div>

  <p><strong>Avg Latency:</strong> {avg_latency}s</p>

  {ragas_section}

  <h2>📂 By Category</h2>
  <table>
    <tr><th>Category</th><th>Passed</th><th>Total</th><th>Rate</th></tr>
    {category_rows}
  </table>

  <h2>🔍 Detailed Results</h2>
  {results_html}
</body>
</html>
"""


def generate_html_report(eval_json_path: str, ragas_scores: Dict = None) -> str:
    with open(eval_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data["summary"]
    results = data["results"]

    # RAGAS section
    ragas_section = ""
    if ragas_scores and "error" not in ragas_scores:
        ragas_section = f"""
        <h2>🔬 RAGAS Metrics</h2>
        <div class="ragas">
          <p><strong>Evaluated on {ragas_scores.get('evaluated_count', 0)} KB queries</strong></p>
          <ul>
            <li><b>Faithfulness:</b> {ragas_scores.get('faithfulness', 'n/a')} (no hallucinations?)</li>
            <li><b>Answer Relevance:</b> {ragas_scores.get('answer_relevancy', 'n/a')} (does it answer the question?)</li>
            <li><b>Context Precision:</b> {ragas_scores.get('context_precision', 'n/a')} (right docs retrieved?)</li>
          </ul>
        </div>
        """
    elif ragas_scores and "error" in ragas_scores:
        ragas_section = f"<h2>🔬 RAGAS Metrics</h2><p><em>Skipped: {ragas_scores['error']}</em></p>"

    # Category rows
    category_rows = ""
    for cat, stats in summary["by_category"].items():
        rate = round(stats["passed"] / max(stats["total"], 1) * 100, 0)
        category_rows += f"<tr><td>{cat}</td><td>{stats['passed']}</td><td>{stats['total']}</td><td>{rate}%</td></tr>"

    # Detailed results
    results_html = ""
    for r in results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        status_class = "pass" if r["passed"] else "fail"
        results_html += f"""
        <details>
          <summary><span class="status {status_class}">{status}</span> &mdash; [{r['category']}] {r['id']}: {r['question'][:80]}</summary>
          <p><b>Question:</b> {r['question']}</p>
          <p><b>Expected:</b> {r.get('expected_answer', 'n/a')}</p>
          <p><b>Actual:</b> {r['actual_answer'][:500]}</p>
          <p><b>Intent:</b> {r.get('actual_intent')} (expected: {r.get('expected_intent')})</p>
          <p><b>Domain:</b> {r.get('actual_domain')} (expected: {r.get('expected_domain')})</p>
          <p><b>Latency:</b> {r['elapsed_sec']}s</p>
        </details>
        """

    html = HTML_TEMPLATE.format(
        timestamp=data.get("timestamp", datetime.now().isoformat()),
        total=summary["total"],
        passed=summary["passed"],
        failed=summary["failed"],
        pass_rate=summary["pass_rate"],
        avg_latency=summary["avg_latency_sec"],
        ragas_section=ragas_section,
        category_rows=category_rows,
        results_html=results_html,
    )

    out_path = Path(eval_json_path).with_suffix(".html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📄 HTML report: {out_path}")
    return str(out_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.evaluation.report <eval_results.json>")
        sys.exit(1)
    generate_html_report(sys.argv[1])