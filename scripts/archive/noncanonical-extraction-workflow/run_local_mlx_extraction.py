#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

DEFAULT_MODEL = "mlx-community/Qwen2.5-3B-Instruct-4bit"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a prepared abstract extraction request batch with MLX."
    )
    parser.add_argument(
        "--requests-path",
        required=True,
        help="Path to prepared requests.jsonl from create_extraction_run.py.",
    )
    parser.add_argument(
        "--responses-path",
        required=True,
        help="Path to write model responses JSONL.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="MLX-compatible model id to load.",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="Optional cap on number of requests to run.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=900,
        help="Maximum tokens to generate per request.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature.",
    )
    return parser.parse_args()


def load_requests(path: Path, max_requests):
    requests = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            requests.append(json.loads(line))
            if max_requests is not None and len(requests) >= max_requests:
                break
    return requests


def extract_first_json_object(text: str):
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object start found")

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    raise ValueError("unterminated JSON object")


def attach_parsed_payload(response, request, parsed_payload):
    if not isinstance(parsed_payload, dict):
        raise ValueError("model output must parse to a JSON object")

    if "mechanism_instances" in parsed_payload:
        # @context decision -- C06 keeps the paper-level wrapper as the canonical runtime output so
        # later review and ingest steps can distinguish real zero-mechanism collapses from legacy
        # single-record responses without reparsing model raw text.
        response["paper_id"] = parsed_payload.get("paper_id", request["paper_id"])
        response["response_contract_version"] = parsed_payload.get(
            "response_contract_version",
            request.get("response_contract_version", "mechanism-instance-batch-v1"),
        )
        if "abstain_reason" in parsed_payload:
            response["abstain_reason"] = parsed_payload["abstain_reason"]
        if "abstain_explanation" in parsed_payload:
            response["abstain_explanation"] = parsed_payload["abstain_explanation"]
        response["mechanism_instances"] = parsed_payload["mechanism_instances"]
        return

    response["extraction"] = parsed_payload


def main():
    args = parse_args()

    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    requests_path = Path(args.requests_path).resolve()
    responses_path = Path(args.responses_path).resolve()
    responses_path.parent.mkdir(parents=True, exist_ok=True)

    requests = load_requests(requests_path, args.max_requests)
    model, tokenizer = load(args.model)
    sampler = make_sampler(temp=args.temperature)

    with responses_path.open("w", encoding="utf-8") as handle:
        for request in requests:
            messages = [{"role": "user", "content": request["prompt"]}]
            prompt = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=False,
            )
            raw_text = generate(
                model,
                tokenizer,
                prompt=prompt,
                verbose=False,
                max_tokens=args.max_tokens,
                sampler=sampler,
            )

            response = {
                "run_id": request["run_id"],
                "paper_id": request["paper_id"],
                "model_name": args.model,
                "request_payload": request.get("request_payload"),
                "raw_text": raw_text,
            }

            try:
                extraction_text = extract_first_json_object(raw_text)
                attach_parsed_payload(
                    response=response,
                    request=request,
                    parsed_payload=json.loads(extraction_text),
                )
                response["parse_status"] = "ok"
            except Exception as exc:
                response["parse_status"] = "parse_error"
                response["parse_error"] = str(exc)

            handle.write(json.dumps(response, sort_keys=True) + "\n")

    print(
        json.dumps(
            {
                "requests_path": str(requests_path),
                "responses_path": str(responses_path),
                "model": args.model,
                "request_count": len(requests),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
