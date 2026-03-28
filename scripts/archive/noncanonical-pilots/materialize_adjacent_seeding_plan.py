#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = ROOT / "configs" / "adjacent_literature_seed_registry.json"
DEFAULT_LEXICON_PATH = ROOT / "configs" / "adjacent_jargon_lexicons.json"
DEFAULT_HOLDOUT_PATH = ROOT / "configs" / "adjacent_holdout_slice.json"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Materialize adjacent-literature seeding and holdout plan artifacts."
    )
    parser.add_argument(
        "--registry-path",
        default=str(DEFAULT_REGISTRY_PATH),
        help="Path to the adjacent-literature seed registry JSON.",
    )
    parser.add_argument(
        "--lexicon-path",
        default=str(DEFAULT_LEXICON_PATH),
        help="Path to the per-family jargon lexicon JSON.",
    )
    parser.add_argument(
        "--holdout-path",
        default=str(DEFAULT_HOLDOUT_PATH),
        help="Path to the holdout-slice policy JSON.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where seeding artifacts should be written.",
    )
    return parser.parse_args()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_payload(registry, lexicons, holdout):
    lexicon_families = set(lexicons["families"].keys())
    active = []
    holdout_families = []
    for family in registry["families"]:
        if family["literature_family"] not in lexicon_families:
            raise SystemExit(f"missing jargon lexicon for {family['literature_family']}")
        payload = dict(family)
        payload["jargon_lexicon"] = lexicons["families"][family["literature_family"]]
        if family["seed_role"] == "holdout":
            holdout_families.append(payload)
        else:
            active.append(payload)

    reserved = set(holdout["reserved_families"])
    for family in holdout_families:
        if family["literature_family"] not in reserved:
            raise SystemExit(
                f"holdout family {family['literature_family']} missing from holdout policy"
            )

    return {
        "version": registry["version"],
        "anchor_corpus": registry["anchor_corpus"],
        "active_families": active,
        "holdout_families": holdout_families,
        "holdout_policy": holdout,
    }


def write_outputs(output_dir: Path, payload):
    output_dir.mkdir(parents=True, exist_ok=True)
    active_path = output_dir / "active_seed_families.json"
    holdout_path = output_dir / "holdout_seed_families.json"
    summary_path = output_dir / "summary.json"

    active_path.write_text(
        json.dumps(payload["active_families"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    holdout_path.write_text(
        json.dumps(
            {
                "families": payload["holdout_families"],
                "policy": payload["holdout_policy"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = {
        "version": payload["version"],
        "anchor_corpus": payload["anchor_corpus"],
        "active_family_count": len(payload["active_families"]),
        "holdout_family_count": len(payload["holdout_families"]),
        "active_family_ids": [
            family["literature_family"] for family in payload["active_families"]
        ],
        "holdout_family_ids": [
            family["literature_family"] for family in payload["holdout_families"]
        ],
        "artifacts": {
            "active": str(active_path.resolve()),
            "holdout": str(holdout_path.resolve()),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary_path


def main():
    args = parse_args()
    payload = build_payload(
        registry=load_json(Path(args.registry_path).resolve()),
        lexicons=load_json(Path(args.lexicon_path).resolve()),
        holdout=load_json(Path(args.holdout_path).resolve()),
    )
    summary_path = write_outputs(Path(args.output_dir).resolve(), payload)
    print(summary_path.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
