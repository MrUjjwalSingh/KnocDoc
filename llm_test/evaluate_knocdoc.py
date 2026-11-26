"""Evaluate KnocDoc's live LLM query parser against the 16-query golden dataset."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "api"))
load_dotenv(ROOT / ".env")

import pandas as pd

from app.config import Settings
from app.search.normalizer import normalize_specialty
from app.search.query_parser import QueryParserError, parse_search_query

DATA_FILE = Path(__file__).resolve().parent / "traveldoc_llm_test_data.xlsx"
GOLD_FILE = Path(__file__).resolve().parent / "traveldoc_golden_dataset.xlsx"


async def evaluate() -> None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is not set.")

    settings = Settings(
        openrouter_api_key=api_key,
        openrouter_model="nvidia/nemotron-3-ultra-550b-a55b:free",
        openrouter_timeout_seconds=30.0,
        openrouter_max_retries=1,
    )

    data_df = pd.read_excel(DATA_FILE, sheet_name="Test Data").fillna("")
    gold_df = pd.read_excel(GOLD_FILE, sheet_name="Golden Dataset").fillna("")
    gold_map = {str(r["id"]): json.loads(r["expected_json"]) for _, r in gold_df.iterrows()}

    metrics = {
        "total": len(data_df),
        "parse_success": 0,
        "specialty_match": 0,
        "languages_match": 0,
        "radius_match": 0,
        "budget_match": 0,
        "profile_match": 0,
        "clarification_match": 0,
        "unanswerable_match": 0,
        "preferences_match": 0,
        "hard_constraints_overlap": 0,
        "errors": [],
        "latencies": [],
    }

    for _, row in data_df.iterrows():
        cid = str(row["id"])
        query = str(row["query"])
        gold = gold_map[cid]
        t0 = time.perf_counter()
        try:
            prefs = await parse_search_query(query, settings=settings)
            lat = round(time.perf_counter() - t0, 2)
            metrics["latencies"].append(lat)
            metrics["parse_success"] += 1

            gold_spec = normalize_specialty(gold.get("specialty"))
            if prefs.specialty == gold_spec:
                metrics["specialty_match"] += 1

            if {l.lower() for l in prefs.languages} == {l.lower() for l in gold.get("languages", [])}:
                metrics["languages_match"] += 1

            if prefs.radius_km == gold.get("radius_km"):
                metrics["radius_match"] += 1

            if prefs.budget_max == gold.get("budget_max"):
                metrics["budget_match"] += 1

            if prefs.ranking_profile == gold.get("ranking_profile", "balanced"):
                metrics["profile_match"] += 1

            if prefs.needs_clarification == bool(gold.get("needs_clarification", False)):
                metrics["clarification_match"] += 1

            if prefs.unanswerable == bool(gold.get("unanswerable", False)):
                metrics["unanswerable_match"] += 1

            if set(prefs.preferences) == set(gold.get("preferences", [])):
                metrics["preferences_match"] += 1

            gold_hc = {c.lower() for c in gold.get("hard_constraints", [])}
            pred_hc = {c.lower() for c in prefs.hard_constraints}
            if not gold_hc or gold_hc.issubset(pred_hc) or len(gold_hc & pred_hc) >= len(gold_hc) * 0.75:
                metrics["hard_constraints_overlap"] += 1

            print(f"[{cid}] OK ({lat}s) profile={prefs.ranking_profile} spec={prefs.specialty}")
        except QueryParserError as exc:
            lat = round(time.perf_counter() - t0, 2)
            metrics["latencies"].append(lat)
            metrics["errors"].append(f"{cid}: {exc.code} ({exc.message})")
            print(f"[{cid}] ERROR ({lat}s): {exc.code} - {exc.message}")

    print("\n=== SUMMARY ===")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    asyncio.run(evaluate())
