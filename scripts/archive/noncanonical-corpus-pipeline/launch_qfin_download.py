#!/usr/bin/env python3
"""Launch the q-fin PDF downloader as a detached background process."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HELPER_DIR = Path(__file__).resolve().parent.parent / "noncanonical-corpus-helpers"
if str(HELPER_DIR) not in sys.path:
    # @context requirement -- archived corpus workflow files import each other
    # by bare module name, so the archive has to add its sibling helper
    # directory explicitly or the preserved workflow breaks after leaving
    # scripts/.
    sys.path.insert(0, str(HELPER_DIR))

from corpus_inventory import build_inventory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=3, help="Concurrent download workers.")
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=1.0,
        help="Minimum delay between request starts across all workers.",
    )
    parser.add_argument(
        "--ids-file",
        type=Path,
        default=Path("data/arxiv-qfin/ids.txt"),
        help="Text file containing one arXiv ID per line.",
    )
    parser.add_argument(
        "--metadata-jsonl",
        type=Path,
        default=Path("data/arxiv-qfin/metadata.jsonl"),
        help="Metadata JSONL used to enrich the manifest.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/arxiv-qfin/pdfs"),
        help="Destination directory for downloaded PDFs.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("logs/qfin_download.log"),
        help="Downloader log file.",
    )
    parser.add_argument(
        "--pid-file",
        type=Path,
        default=Path("logs/qfin_download.pid"),
        help="Downloader PID file.",
    )
    parser.add_argument(
        "--launch-metadata",
        type=Path,
        default=Path("logs/qfin_download.launch.json"),
        help="Launch metadata JSON written after successful start.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=4,
        help="Retries per PDF request.",
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Launch the pipeline runner instead of the raw downloader.",
    )
    parser.add_argument(
        "--retry-passes",
        type=int,
        default=1,
        help="Retry passes for pipeline mode.",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Terminate an existing running downloader before launching a new one.",
    )
    return parser.parse_args()


def pid_running(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    raw = pid_file.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    pid = int(raw)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        return pid
    return pid


def stop_process(pid: int) -> None:
    os.kill(pid, signal.SIGTERM)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def build_command(args: argparse.Namespace) -> list[str]:
    if args.pipeline:
        return [
            sys.executable,
            "-u",
            str(Path(__file__).resolve().parent / "run_qfin_pipeline.py"),
            "--data-dir",
            str(args.output_dir.parent),
            "--ids-file",
            str(args.ids_file),
            "--metadata-jsonl",
            str(args.metadata_jsonl),
            "--output-dir",
            str(args.output_dir),
            "--workers",
            str(args.workers),
            "--delay-seconds",
            str(args.delay_seconds),
            "--retries",
            str(args.retries),
            "--retry-passes",
            str(args.retry_passes),
        ]
    return [
        sys.executable,
        "-u",
        "scripts/download_arxiv_pdfs.py",
        "--metadata-jsonl",
        str(args.metadata_jsonl),
        "--workers",
        str(args.workers),
        "--delay-seconds",
        str(args.delay_seconds),
        "--ids-file",
        str(args.ids_file),
        "--output-dir",
        str(args.output_dir),
        "--retries",
        str(args.retries),
        "--skip-existing",
    ]


def write_launch_metadata(path: Path, pid: int, command: list[str]) -> None:
    payload = {
        "pid": pid,
        "command": command,
        "launched_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    ensure_parent(args.log_file)
    ensure_parent(args.pid_file)
    ensure_parent(args.launch_metadata)

    running_pid = pid_running(args.pid_file)
    if running_pid and not args.restart:
        print(f"downloader already running with pid {running_pid}", file=sys.stderr)
        return 1
    if running_pid and args.restart:
        stop_process(running_pid)

    build_inventory(args.output_dir.parent, args.output_dir.parent / "inventory")

    command = build_command(args)
    with args.log_file.open("a", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            command,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            cwd=Path.cwd(),
        )

    args.pid_file.write_text(f"{process.pid}\n", encoding="utf-8")
    write_launch_metadata(args.launch_metadata, process.pid, command)
    print(process.pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
