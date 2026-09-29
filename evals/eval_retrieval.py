"""
Path A, step 3: the retrieval eval. Checks whether the retriever finds the right ticket
for each question in eval_dataset.json.

    python -m retrieval.build_index      # index the sample tickets first
    python -m evals.eval_retrieval

Each question has exactly one correct ticket, so:
  hit@1  = right ticket ranked first
  hit@k  = right ticket anywhere in the top k (this is recall@k with one relevant ticket)
  MRR    = mean reciprocal rank: 1 for rank 1, 1/2 for rank 2, 1/3 for rank 3, 0 if missed

Exits with code 1 when a score is below its threshold, so CI fails on a regression.
"""
import argparse
import json
import sys

from retrieval.jira_retriever import retrieve

DATASET = "evals/eval_dataset.json"


def reciprocal_rank(expected: str, got: list) -> float:
    return 1 / (got.index(expected) + 1) if expected in got else 0.0


def run_eval(k: int = 3, dataset_path: str = DATASET) -> dict:
    with open(dataset_path) as f:
        dataset = json.load(f)

    hits_at_1, hits_at_k, rr_total = 0, 0, 0.0
    for case in dataset:
        got = [ticket_id for _, ticket_id in retrieve(case["query"], k=k)]
        expected = case["expected_ticket"]
        rank = got.index(expected) + 1 if expected in got else None

        hits_at_1 += rank == 1
        hits_at_k += rank is not None
        rr_total += reciprocal_rank(expected, got)

        status = "PASS" if rank == 1 else ("RANK " + str(rank) if rank else "MISS")
        print(f"{status:<7} {case['query']}\n        expected {expected}, got {got}")

    n = len(dataset)
    return {"cases": n, "hit@1": hits_at_1 / n, f"hit@{k}": hits_at_k / n, "mrr": rr_total / n}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score Jira retrieval against eval_dataset.json")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--min-hit-at-k", type=float, default=0.0, help="fail below this hit@k")
    parser.add_argument("--min-mrr", type=float, default=0.0, help="fail below this MRR")
    args = parser.parse_args()

    scores = run_eval(k=args.k)
    print(f"\nCases: {scores['cases']}")
    print(f"hit@1: {scores['hit@1']:.0%}")
    print(f"hit@{args.k}: {scores[f'hit@{args.k}']:.0%}")
    print(f"MRR:   {scores['mrr']:.2f}")

    failed = scores[f"hit@{args.k}"] < args.min_hit_at_k or scores["mrr"] < args.min_mrr
    if failed:
        print(f"\nFAILED: below threshold (hit@{args.k} >= {args.min_hit_at_k}, MRR >= {args.min_mrr})")
    sys.exit(1 if failed else 0)
