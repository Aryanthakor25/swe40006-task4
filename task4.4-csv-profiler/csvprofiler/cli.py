"""Command-line interface.

    csvprofiler profile FILE          profile one CSV file
    csvprofiler profile-all           profile every *.csv in the input folder
    csvprofiler history               show previous runs (stored in SQLite)
    csvprofiler watch                 keep running and profile new files as they appear

Exit codes: 0 = success, 2 = bad arguments, 3 = input not found, 4 = nothing profiled / bad CSV,
            5 = output folder not writable
"""
import argparse
import logging
import os
import signal
import socket
import sys
import time
from pathlib import Path

from . import __version__
from .history import History, file_sha256
from .profiler import ProfileError, profile_csv, write_outputs

EXIT_OK, EXIT_NOT_FOUND, EXIT_FAILED, EXIT_OUTPUT = 0, 3, 4, 5

log = logging.getLogger("csvprofiler")


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        stream=sys.stdout,
    )


def _output_writable(out_dir: Path) -> bool:
    """Fail early with a clear message instead of a PermissionError traceback."""
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        probe = out_dir / ".write-test"
        probe.write_text("ok")
        probe.unlink()
        return True
    except OSError as exc:
        log.error("Cannot write to output folder %s (%s). Running as uid %s. "
                  "On a Linux host give the bind-mounted folder to that uid, e.g. "
                  "`sudo chown -R 10001:10001 ./data/output`.",
                  out_dir, exc.strerror, os.getuid())
        return False


def _process(path: Path, out_dir: Path, history: History, skip_seen: bool = False) -> bool:
    digest = file_sha256(path)
    if skip_seen and history.already_processed(digest):
        log.debug("Skipping %s (already profiled)", path.name)
        return True
    start = time.perf_counter()
    try:
        profile = profile_csv(path)
    except ProfileError as exc:
        history.record(path.name, digest, None, None, 0, "error")
        log.error("Failed to profile %s: %s", path.name, exc)
        return False
    outputs = write_outputs(profile, out_dir)
    ms = int((time.perf_counter() - start) * 1000)
    history.record(path.name, digest, profile["rows"], profile["columns"], ms, "ok")
    log.info("Profiled %s: %d rows x %d cols, completeness %.2f%% (%d ms), wrote %s",
             path.name, profile["rows"], profile["columns"], profile["completeness_pct"], ms,
             ", ".join(p.name for p in outputs))
    return True


def cmd_profile(args, history: History) -> int:
    path = Path(args.file)
    if not path.is_absolute() and not path.exists():
        path = Path(args.input) / path  # allow just the file name
    if not path.is_file():
        log.error("Input file not found: %s", path)
        return EXIT_NOT_FOUND
    if not _output_writable(Path(args.output)):
        return EXIT_OUTPUT
    return EXIT_OK if _process(path, Path(args.output), history) else EXIT_FAILED


def cmd_profile_all(args, history: History) -> int:
    in_dir = Path(args.input)
    if not in_dir.is_dir():
        log.error("Input folder not found: %s", in_dir)
        return EXIT_NOT_FOUND
    files = sorted(in_dir.glob("*.csv"))
    if not files:
        log.warning("No .csv files in %s", in_dir)
        return EXIT_FAILED
    if not _output_writable(Path(args.output)):
        return EXIT_OUTPUT
    log.info("Found %d CSV file(s) in %s", len(files), in_dir)
    ok = sum(_process(f, Path(args.output), history) for f in files)
    log.info("Done: %d succeeded, %d failed", ok, len(files) - ok)
    return EXIT_OK if ok == len(files) else EXIT_FAILED


def cmd_history(args, history: History) -> int:
    rows = history.recent(args.limit)
    if not rows:
        print("No runs recorded yet.")
        return EXIT_OK
    header = f"{'ID':>4}  {'RUN AT (UTC)':<25}  {'CONTAINER':<12}  {'FILE':<28}  {'ROWS':>6}  {'COLS':>4}  {'MS':>5}  STATUS"
    print(header)
    print("-" * len(header))
    for rid, run_at, container, file, nrows, ncols, ms, status in rows:
        print(f"{rid:>4}  {run_at:<25}  {container[:12]:<12}  {file[:28]:<28}  "
              f"{nrows if nrows is not None else '-':>6}  {ncols if ncols is not None else '-':>4}  "
              f"{ms if ms is not None else '-':>5}  {status}")
    return EXIT_OK


def cmd_watch(args, history: History) -> int:
    in_dir = Path(args.input)
    if not in_dir.is_dir():
        log.error("Input folder not found: %s", in_dir)
        return EXIT_NOT_FOUND

    if not _output_writable(Path(args.output)):
        return EXIT_OUTPUT

    stopping = {"flag": False}

    def _stop(signum, _frame):
        log.info("Received %s, finishing current work and shutting down", signal.Signals(signum).name)
        stopping["flag"] = True

    # `docker stop` sends SIGTERM; Ctrl+C sends SIGINT
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    log.info("Watching %s every %ss (container %s)", in_dir, args.interval, socket.gethostname())
    while not stopping["flag"]:
        for f in sorted(in_dir.glob("*.csv")):
            if stopping["flag"]:
                break
            _process(f, Path(args.output), history, skip_seen=True)
        # sleep in short steps so a stop signal is handled quickly
        waited = 0.0
        while waited < args.interval and not stopping["flag"]:
            time.sleep(0.2)
            waited += 0.2
    log.info("Watcher stopped cleanly")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--input", default=os.getenv("PROFILER_INPUT", "data/input"),
                        help="input folder (env PROFILER_INPUT)")
    common.add_argument("--output", default=os.getenv("PROFILER_OUTPUT", "data/output"),
                        help="output folder (env PROFILER_OUTPUT)")
    common.add_argument("--db", default=os.getenv("PROFILER_DB", "data/history.db"),
                        help="SQLite history file (env PROFILER_DB)")
    common.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "info"))

    p = argparse.ArgumentParser(prog="csvprofiler", description="Profile CSV files and keep a run history.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("profile", parents=[common], help="profile a single CSV file")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_profile)

    sp = sub.add_parser("profile-all", parents=[common], help="profile every CSV in the input folder")
    sp.set_defaults(func=cmd_profile_all)

    sp = sub.add_parser("history", parents=[common], help="show previous runs")
    sp.add_argument("--limit", type=int, default=20)
    sp.set_defaults(func=cmd_history)

    sp = sub.add_parser("watch", parents=[common], help="profile new files as they arrive")
    sp.add_argument("--interval", type=float, default=float(os.getenv("WATCH_INTERVAL", "5")))
    sp.set_defaults(func=cmd_watch)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    _setup_logging(args.log_level)
    log.debug("csvprofiler %s starting: %s", __version__, args.command)
    history = History(Path(args.db))
    try:
        return args.func(args, history)
    finally:
        history.close()
