"""Offline eval runner: score the RAG pipeline against the golden set.

Run:  uv run python -m app.eval.runner
      uv run python -m app.eval.runner --prompt v2
      uv run python -m app.eval.runner --compare v1 v2
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from openai import AsyncAzureOpenAI

from app.config import Settings, get_settings
from app.eval import metrics
from app.eval.golden_set import GOLDEN, GoldenQuestion
from app.services.generation.generator import generate_answer
from app.services.generation.prompts import PROMPT_VERSION, get_prompt
from app.services.retrieval.retriever import hybrid_search
from app.services.storage.search import make_search_client


def _make_eval_client(settings: Settings) -> AsyncAzureOpenAI:
    # generous retries — eval fires many judge calls and hits limited-tier 429s
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        timeout=60.0,
        max_retries=8,
    )


_REPORTS_DIR = Path(__file__).parent / "reports"
_METRIC_KEYS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


async def _evaluate_one(client, search, settings, gq: GoldenQuestion, system_prompt: str) -> dict:
    chat_deployment = settings.azure_openai_chat_deployment
    embedding_deployment = settings.azure_openai_embedding_deployment

    chunks = await hybrid_search(search, client, embedding_deployment, gq.question)
    contexts = [c["content"] for c in chunks]
    answer = await generate_answer(
        client, chat_deployment, gq.question, chunks, system_prompt=system_prompt
    )

    # Sequential — parallel metric calls burst past the rate limit.
    faith = await metrics.faithfulness(client, chat_deployment, answer, contexts)
    ans_rel = await metrics.answer_relevancy(
        client, embedding_deployment, chat_deployment, gq.question, answer
    )
    ctx_prec = await metrics.context_precision(
        client, chat_deployment, gq.question, gq.ground_truth, contexts
    )
    ctx_rec = await metrics.context_recall(client, chat_deployment, gq.ground_truth, contexts)
    return {
        "question": gq.question,
        "ground_truth": gq.ground_truth,
        "answer": answer,
        "num_contexts": len(contexts),
        "faithfulness": round(faith, 3),
        "answer_relevancy": round(ans_rel, 3),
        "context_precision": round(ctx_prec, 3),
        "context_recall": round(ctx_rec, 3),
    }


def _mean(rows: list[dict], key: str) -> float:
    return round(sum(r[key] for r in rows) / len(rows), 3) if rows else 0.0


async def run(prompt_version: str = PROMPT_VERSION) -> dict:
    system_prompt = get_prompt(prompt_version)  # raises KeyError on unknown version
    settings = get_settings()
    client = _make_eval_client(settings)
    search = make_search_client(settings)
    try:
        # Sequential — each question fans out to ~6 metric calls; parallelising both layers hits rate limits.
        rows = [await _evaluate_one(client, search, settings, gq, system_prompt) for gq in GOLDEN]
    finally:
        await client.close()
        await search.close()

    aggregate = {k: _mean(rows, k) for k in _METRIC_KEYS}
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "prompt_version": prompt_version,
        "num_questions": len(rows),
        "aggregate": aggregate,
        "results": rows,
    }

    _REPORTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_path = _REPORTS_DIR / f"eval_{prompt_version}_{stamp}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    _print_summary(report, out_path)
    return report


async def compare(versions: list[str]) -> None:
    """Score several prompt versions against the golden set and diff their aggregates."""
    reports = [await run(v) for v in versions]
    print("\n" + "=" * 60)
    print(f"PORÓWNANIE PROMPTÓW: {', '.join(versions)}\n")
    header = f"{'metryka':<20}" + "".join(f"{v:>10}" for v in versions)
    print(header)
    print("-" * len(header))
    for k in _METRIC_KEYS:
        row = f"{k:<20}" + "".join(f"{r['aggregate'][k]:>10}" for r in reports)
        print(row)
    means = [sum(r["aggregate"].values()) / len(_METRIC_KEYS) for r in reports]
    best = versions[means.index(max(means))]
    print("-" * len(header))
    print(f"{'ŚREDNIA ŁĄCZNA':<20}" + "".join(f"{m:>10.3f}" for m in means))
    print(f"\n🏆 Najlepszy: {best}")


def _print_summary(report: dict, out_path: Path) -> None:
    print(f"\nEval — prompt {report['prompt_version']} — {report['num_questions']} pytań\n")
    header = f"{'pytanie':<45} {'faith':>6} {'a_rel':>6} {'c_prec':>7} {'c_rec':>6}"
    print(header)
    print("-" * len(header))
    for r in report["results"]:
        q = (r["question"][:42] + "…") if len(r["question"]) > 43 else r["question"]
        print(
            f"{q:<45} {r['faithfulness']:>6} {r['answer_relevancy']:>6} "
            f"{r['context_precision']:>7} {r['context_recall']:>6}"
        )
    agg = report["aggregate"]
    print("-" * len(header))
    print(
        f"{'ŚREDNIA':<45} {agg['faithfulness']:>6} {agg['answer_relevancy']:>6} "
        f"{agg['context_precision']:>7} {agg['context_recall']:>6}"
    )
    print(f"\nRaport zapisany: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eval the RAG pipeline against the golden set.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--prompt", default=PROMPT_VERSION, help="prompt version to score")
    group.add_argument("--compare", nargs="+", metavar="V", help="score & diff several versions")
    args = parser.parse_args()

    if args.compare:
        asyncio.run(compare(args.compare))
    else:
        asyncio.run(run(args.prompt))
