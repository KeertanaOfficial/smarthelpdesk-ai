import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


# ============================================================
# Common output schema
# ============================================================
def normalize_entry(
    id: str,
    question: str,
    answer: str,
    category: str = "General",
    subcategory: str = "",
    domain: str = "unknown",
    source: str = "",
    priority: Optional[str] = None,
) -> Dict:
    return {
        "id": id,
        "domain": (domain or "unknown").strip().lower(),
        "category": (category or "General").strip(),
        "subcategory": (subcategory or "").strip(),
        "question": (question or "").strip(),
        "answer": (answer or "").strip(),
        "source": source or "unknown",
        "priority": priority or "",
    }


# ============================================================
# Utility: infer domain if missing
# ============================================================
def infer_domain(category: str, question: str = "") -> str:
    text = f"{category} {question}".lower()
    if "hr" in text or "leave" in text or "payroll" in text or "onboarding" in text or "benefit" in text or "reimbursement" in text:
        return "hr"
    if "it" in text or "vpn" in text or "password" in text or "mfa" in text or "wifi" in text or "software" in text or "email" in text:
        return "it"
    return "unknown"


# ============================================================
# Loader 1: curated JSON
# ============================================================
def load_json_kb(path: Path) -> List[Dict]:
    if not path.exists():
        print(f"[loader] Missing: {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    entries = []
    for r in raw:
        entries.append({
            "id": r.get("id"),
            "domain": r.get("domain", "unknown"),   # ✅ CRITICAL
            "category": r.get("category", "General"),
            "question": r.get("question", "").strip(),
            "answer": r.get("answer", "").strip(),
            "source": "kb_json"
        })

    return entries

# ============================================================
# Loader 3: strova-ai/hr-policies-qa-dataset
# messages format
# ============================================================
def load_strova_hr(path: Path) -> List[Dict]:
    if not path.exists():
        return []

    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            try:
                row = json.loads(line)
                messages = row.get("messages", [])
                user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
                bot_msg = next((m["content"] for m in messages if m["role"] == "assistant"), "")

                if user_msg and bot_msg:
                    entries.append(
                        normalize_entry(
                            id=f"strova_{i:04d}",
                            question=user_msg,
                            answer=bot_msg,
                            category="Policy",
                            subcategory="GeneralHR",
                            domain="hr",
                            source="strova-ai/hr-policies-qa-dataset",
                        )
                    )
            except Exception:
                continue
    return entries


# ============================================================
# Loader 4: EmbraceCoder/HR_Policy
# ============================================================
def load_embracecoder_hr(path: Path) -> List[Dict]:
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    entries = []
    pattern = re.compile(r"<human>:\s*(.+?)\s*<bot>:\s*(.+?)(?=<human>:|$)", re.DOTALL)

    for i, row in enumerate(rows):
        text = row.get("text", "")
        matches = pattern.findall(text)
        for j, (q, a) in enumerate(matches):
            entries.append(
                normalize_entry(
                    id=f"embracecoder_{i:04d}_{j:02d}",
                    question=q.strip(),
                    answer=a.strip(),
                    category="Policy",
                    subcategory="GeneralHR",
                    domain="hr",
                    source="EmbraceCoder/HR_Policy",
                )
            )
    return entries


# ============================================================
# Loader 5: Console-AI IT tickets
# ============================================================
def load_console_it(path: Path, max_rows: int = 500) -> List[Dict]:
    if not path.exists():
        return []

    df = pd.read_csv(path).head(max_rows)
    entries = []

    for _, row in df.iterrows():
        subject = str(row.get("subject", "")).strip()
        description = str(row.get("description", "")).strip()
        category = str(row.get("category", "General")).strip()
        priority = str(row.get("priority", "Medium")).strip()

        if not subject or not description:
            continue

        entries.append(
            normalize_entry(
                id=f"console_{row.get('id', '')}",
                question=subject,
                answer=f"Issue details: {description}",
                category=category,
                subcategory="Ticket",
                domain="it",
                source="Console-AI/IT-helpdesk-synthetic-tickets",
                priority=priority,
            )
        )
    return entries


# ============================================================
# Loader 6: KameronB IT tickets
# ============================================================
def load_kameron_it(path: Path, max_rows: int = 500) -> List[Dict]:
    if not path.exists():
        return []

    df = pd.read_csv(path).head(max_rows)
    entries = []

    for i, row in enumerate(df.iterrows()):
        _, row = row
        short_desc = str(row.get("short_description", "")).strip()
        content = str(row.get("content", "")).strip()
        close_notes = str(row.get("close_notes", "")).strip()
        category = str(row.get("category", "General")).strip()
        subcategory = str(row.get("subcategory", "")).strip()

        if not short_desc:
            continue

        if close_notes and close_notes.lower() != "nan":
            answer = f"Resolution: {close_notes}"
        elif content:
            answer = f"Issue context: {content}"
        else:
            continue

        entries.append(
            normalize_entry(
                id=f"kameron_{i:05d}",
                question=short_desc,
                answer=answer,
                category=category,
                subcategory=subcategory,
                domain="it",
                source="KameronB/synthetic-it-callcenter-tickets",
            )
        )
    return entries


# ============================================================
# Aggregator
# ============================================================
# Deduplicate by id (assuming each source has unique ID patterns)
def dedupe(entries: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for e in entries:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        out.append(e)
    return out


def build_full_kb() -> Dict[str, List[Dict]]:
    hr_entries = []
    it_entries = []

    # HR
    hr_path = Path("data/kb/hr_kb.json")
    if hr_path.exists():
        hr = load_json_kb(hr_path)
        hr_entries += [x for x in hr if x["domain"] == "hr"]
        print(f"✅ HR loaded: {len(hr_entries)}")

    # IT
    it_path = Path("data/kb/it_kb.json")
    if it_path.exists():
        it = load_json_kb(it_path)
        it_entries += [x for x in it if x["domain"] == "it"]
        print(f"✅ IT loaded: {len(it_entries)}")

    return {
        "hr": dedupe(hr_entries),
        "it": dedupe(it_entries)
    }

def save_processed(kb: Dict[str, List[Dict]]):
    proc_dir = Path("data/kb/processed")
    proc_dir.mkdir(parents=True, exist_ok=True)

    for domain, entries in kb.items():
        out_path = proc_dir / f"{domain}_processed.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        print(f"[loader] {domain.upper()}: {len(entries)} entries → {out_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("🔨 Building Full KB")
    print("=" * 60)

    kb = build_full_kb()

    print("\n💾 Saving processed datasets...")
    save_processed(kb)

    print("\n" + "=" * 60)
    print(f"📊 Final: HR={len(kb['hr'])}, IT={len(kb['it'])}, Total={len(kb['hr']) + len(kb['it'])}")
    print("=" * 60)