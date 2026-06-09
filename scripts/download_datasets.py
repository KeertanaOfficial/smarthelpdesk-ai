"""
Download official datasets for SmartHelpDesk AI.

Datasets:
- strova-ai/hr-policies-qa-dataset       (HR Q&A, 644 rows)
- EmbraceCoder/HR_Policy                 (HR snippets, 123 rows)
- Console-AI/IT-helpdesk-synthetic-tickets (IT tickets, 500 rows)
- KameronB/synthetic-it-callcenter-tickets (IT call-center, 27.6K → subset)
"""

from datasets import load_dataset
from pathlib import Path

RAW_DIR = Path("data/kb/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


def download_strova_hr():
    print("\n📥 [1/4] Downloading strova-ai/hr-policies-qa-dataset...")
    ds = load_dataset("strova-ai/hr-policies-qa-dataset", split="train")
    df = ds.to_pandas()
    out = RAW_DIR / "strova_hr.jsonl"
    df.to_json(out, orient="records", lines=True)
    print(f"   ✅ {len(df)} rows → {out}")


def download_embracecoder_hr():
    print("\n📥 [2/4] Downloading EmbraceCoder/HR_Policy...")
    ds = load_dataset("EmbraceCoder/HR_Policy", split="train")
    df = ds.to_pandas()
    out = RAW_DIR / "embracecoder_hr.json"
    df.to_json(out, orient="records")
    print(f"   ✅ {len(df)} rows → {out}")


def download_console_it():
    print("\n📥 [3/4] Downloading Console-AI/IT-helpdesk-synthetic-tickets...")
    ds = load_dataset("Console-AI/IT-helpdesk-synthetic-tickets", split="train")
    df = ds.to_pandas()
    out = RAW_DIR / "console_it_tickets.csv"
    df.to_csv(out, index=False)
    print(f"   ✅ {len(df)} rows → {out}")


def download_kameron_it(subset_size: int = 500):
    print(f"\n📥 [4/4] Downloading KameronB/synthetic-it-callcenter-tickets (subset {subset_size})...")
    ds = load_dataset("KameronB/synthetic-it-callcenter-tickets", split="train")
    df = ds.to_pandas()

    # Sample diverse categories (stratified)
    if "category" in df.columns:
        df = df.groupby("category", group_keys=False).apply(
            lambda g: g.sample(min(len(g), max(1, subset_size // df["category"].nunique())), random_state=42)
        ).reset_index(drop=True)
        df = df.head(subset_size)
    else:
        df = df.sample(n=min(subset_size, len(df)), random_state=42)

    out = RAW_DIR / "kameron_it_tickets.csv"
    df.to_csv(out, index=False)
    print(f"   ✅ {len(df)} rows → {out}")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Downloading SmartHelpDesk AI Datasets")
    print("=" * 60)
    download_strova_hr()
    download_embracecoder_hr()
    download_console_it()
    download_kameron_it(subset_size=500)
    print("\n" + "=" * 60)
    print("✅ All datasets downloaded!")
    print("=" * 60)