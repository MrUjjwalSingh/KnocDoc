"""
KnocDoc LLM benchmark runner
------------------------------
Runs 16 KnocDoc query-parsing test cases against five OpenRouter models,
compares normalized outputs with the separate golden dataset, and writes a
results workbook.

Install:
    pip install openai pandas openpyxl

PowerShell:
    $env:OPENROUTER_API_KEY="your_key_here"
    python benchmark_KnocDoc.py

Git Bash:
    export OPENROUTER_API_KEY="your_key_here"
    python benchmark_KnocDoc.py

Input files (keep beside this script):
    KnocDoc_llm_test_data.xlsx
    KnocDoc_golden_dataset.xlsx

Notes:
- OpenRouter model availability/free limits can change. Model IDs below are
  exactly the IDs supplied for this benchmark; verify them in OpenRouter if a
  model returns 404 or a provider error.
- This benchmark measures query-interpretation consistency, not whether actual
  doctors exist. No provider database is queried.
- Exact JSON match is intentionally strict; use field-level results to diagnose
  near-matches rather than treating exact match as the only quality measure.
"""

import os
import json
import time
import re
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "traveldoc_llm_test_data.xlsx"
GOLD_FILE = BASE_DIR / "traveldoc_golden_dataset.xlsx"
RESULT_FILE = BASE_DIR / "traveldoc_llm_benchmark_results.xlsx"

MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3.5-lightning:free",
    "baidu/ernie-5.5-flash-preview:free",
    "google/gemma-4-26b-a4b-it:free",
]

SYSTEM_PROMPT = """
You are KnocDocs's natural-language search query parser.
KnocDoc is a medical directory, not a diagnosis or treatment service.
Extract only intent explicitly stated or safely implied by the query. Never
invent provider facts or claim a doctor exists. Return ONLY one valid JSON
object with exactly these keys:
{
  "specialty": string or null,
  "languages": array of strings,
  "budget_max": number or null,
  "location": string or null,
  "radius_km": number or null,
  "min_experience_years": number or null,
  "availability": string or null,
  "hard_constraints": array of strings,
  "preferences": array of strings,
  "ranking_profile": one of "balanced", "nearest", "budget_focused",
                      "experience_focused",
  "needs_clarification": boolean,
  "unanswerable": boolean
}
Rules:
- Normalize common specialty names to these where applicable:
  cardiology, dermatology, pediatrics, general_practice.
- Do not turn a preference ("prefer", "ideally", "I'd rather") into a hard
  constraint unless the user explicitly says mandatory, must, only, never, or
  an equivalent.
- For "under", "below", "no more than", or "at most", set budget_max to that
  numeric amount. For "exactly ₹X", set budget_max to X and include
  "budget_exact:X" in hard_constraints.
- Convert miles to km (1 mile = 1.60934 km), rounded to 2 decimals.
- "nearby" without a distance means distance preference; radius_km remains null.
- Availability values: "open_now", "open_today", "open_24_7_preferred",
  or "tomorrow_HH:MM" when applicable.
- Include normalized hard constraints in hard_constraints. Examples:
  "specialty:cardiology", "language:Hindi", "language_any:Hindi|English",
  "verification:verified", "budget_max:800", "budget_exact:500",
  "radius_km:5", "min_experience_years:10", "availability:open_now".
- Preference values should be concise canonical names: distance, cost,
  language, experience, rating, verification, availability.
- Ranking profile should reflect the strongest stated preference; use balanced
  when there is no clear dominant preference.
- Set needs_clarification true if the user asks for exact current-location
  matching but the current location is not supplied, or if critical required
  details are missing to complete the request.
- Set unanswerable true for impossible/nonexistent entities, requests for
  certainty/guarantees about diagnosis, or when the query explicitly says not
  to guess and required facts cannot be confirmed from the directory. Do not
  give medical advice.
- For the current-location test, use location "current_location_unavailable".
- Return no markdown fences and no explanatory text.
"""

def extract_json(text: str) -> dict[str, Any]:
    """Parse model JSON, allowing accidental markdown fences or surrounding text."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"No JSON object found in model response: {text[:300]}")
    parsed = json.loads(text[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Model response JSON was not an object.")
    return parsed

def canonical(value: Any) -> str:
    """Stable JSON representation for strict comparison."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def main() -> None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit(
            "Missing OPENROUTER_API_KEY. Set it in your terminal environment; "
            "do not hard-code your key in this script."
        )
    if not DATA_FILE.exists() or not GOLD_FILE.exists():
        raise SystemExit(
            "Input workbook(s) not found. Keep both Excel files beside this script."
        )

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://KnocDoc.local",
            "X-Title": "KnocDoc LLM Benchmark",
        },
    )

    data_df = pd.read_excel(DATA_FILE, sheet_name="Test Data").fillna("")
    gold_df = pd.read_excel(GOLD_FILE, sheet_name="Golden Dataset").fillna("")
    gold_map = {
        str(row["id"]): json.loads(row["expected_json"])
        for _, row in gold_df.iterrows()
    }

    results = []
    total_calls = len(data_df) * len(MODELS)
    call_num = 0

    for model in MODELS:
        print(f"\\n=== Model: {model} ===")
        for _, row in data_df.iterrows():
            case_id = str(row["id"])
            query = str(row["query"])
            call_num += 1
            print(f"[{call_num}/{total_calls}] {case_id} ({row['difficulty']})", end=" ... ", flush=True)
            started = time.perf_counter()
            raw = ""
            parsed = None
            error = ""
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": query},
                    ],
                    temperature=0,
                    max_tokens=900,
                )
                raw = response.choices[0].message.content or ""
                parsed = extract_json(raw)
                print("OK")
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                print("ERROR")

            latency_s = round(time.perf_counter() - started, 3)
            gold = gold_map.get(case_id, {})
            row_result = {
                "model": model,
                "id": case_id,
                "difficulty": str(row["difficulty"]),
                "query": query,
                "latency_seconds": latency_s,
                "parse_success": parsed is not None,
                "exact_match": parsed is not None and canonical(parsed) == canonical(gold),
                "error": error,
                "raw_response": raw,
                "parsed_json": json.dumps(parsed, ensure_ascii=False) if parsed is not None else "",
                "golden_json": json.dumps(gold, ensure_ascii=False),
            }

            # Field-level comparison helps diagnose near-matches.
            if parsed is not None:
                for key in gold:
                    row_result[f"match_{key}"] = canonical(parsed.get(key)) == canonical(gold.get(key))
            else:
                for key in gold:
                    row_result[f"match_{key}"] = False
            results.append(row_result)

            # Gentle delay to reduce the chance of hitting free-tier rate limits.
            time.sleep(1.0)

    results_df = pd.DataFrame(results)
    summary_rows = []
    for model in MODELS:
        mdf = results_df[results_df["model"] == model]
        summary_rows.append({
            "model": model,
            "cases": len(mdf),
            "parse_success_count": int(mdf["parse_success"].sum()),
            "parse_success_rate": round(float(mdf["parse_success"].mean()), 4) if len(mdf) else 0,
            "exact_matches": int(mdf["exact_match"].sum()),
            "exact_match_rate": round(float(mdf["exact_match"].mean()), 4) if len(mdf) else 0,
            "avg_latency_seconds": round(float(mdf["latency_seconds"].mean()), 3) if len(mdf) else None,
            "errors": int((mdf["error"] != "").sum()),
        })
    summary_df = pd.DataFrame(summary_rows)

    with pd.ExcelWriter(RESULT_FILE, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        results_df.to_excel(writer, index=False, sheet_name="Detailed Results")
        for sheet_name, df in [("Summary", summary_df), ("Detailed Results", results_df)]:
            ws = writer.book[sheet_name]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for col_cells in ws.columns:
                max_len = max((len(str(cell.value or "")) for cell in col_cells[:100]), default=10)
                width = min(max(max_len + 2, 12), 55)
                ws.column_dimensions[col_cells[0].column_letter].width = width
            if sheet_name == "Detailed Results":
                for col_letter in ["D", "I", "J", "K"]:
                    if col_letter in ws.column_dimensions:
                        ws.column_dimensions[col_letter].width = 65
                for row in ws.iter_rows(min_row=2):
                    for cell in row:
                        if cell.column in (4, 9, 10, 11):
                            cell.alignment = __import__("openpyxl").styles.Alignment(
                                wrap_text=True, vertical="top"
                            )

    print(f"\\nDone. Results saved to: {RESULT_FILE}")
    print("Review Summary first, then Detailed Results and field-level match columns.")

if __name__ == "__main__":
    main()
