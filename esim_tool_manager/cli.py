from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .catalog import TOOLS
from .config import ConfigError, config_path, load_config, save_config
from .manager import (
    all_statuses,
    check_updates,
    log_action,
    read_log_tail,
    run_package_action,
)


def _add_tool_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("tool", choices=tuple(TOOLS), help="Tool key from the catalog.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="esim-tool-manager",
        description="Check and manage external tools used by eSim.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="Show supported tools and detected versions.")
    commands.add_parser("check", help="Check required tools and configured minimum versions.")
    updates = commands.add_parser(
        "updates",
        help="Check for package-manager updates without installing them.",
    )
    updates.add_argument(
        "tool",
        nargs="?",
        choices=tuple(TOOLS),
        help="Optional tool key; omit it to check every supported tool.",
    )

    for action in ("install", "update"):
        action_parser = commands.add_parser(action, help=f"Plan or run a tool {action}.")
        _add_tool_argument(action_parser)
        action_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the package-manager command without running it.",
        )
        action_parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip the confirmation prompt. Use only when you intend to install/update.",
        )

    config_parser = commands.add_parser("config", help="Manage per-user tool settings.")
    config_commands = config_parser.add_subparsers(dest="config_command", required=True)
    config_commands.add_parser("show", help="Show the current configuration.")

    set_path = config_commands.add_parser("set-path", help="Set a custom executable path.")
    _add_tool_argument(set_path)
    set_path.add_argument("path", help="Full path to the tool executable.")

    set_minimum = config_commands.add_parser(
        "set-min-version",
        help="Require a minimum numeric version during dependency checks.",
    )
    _add_tool_argument(set_minimum)
    set_minimum.add_argument("version", help="For example: 9.0 or 9.0.1.")

    clear_path = config_commands.add_parser(
        "clear-path", help="Remove a custom executable path."
    )
    _add_tool_argument(clear_path)

    clear_minimum = config_commands.add_parser(
        "clear-min-version", help="Remove a configured minimum version."
    )
    _add_tool_argument(clear_minimum)

    logs = commands.add_parser("logs", help="Show recent install/update actions.")
    logs.add_argument("--lines", type=int, default=20, help="Number of lines to show.")
    return parser


def _print_statuses(statuses: list) -> None:
    rows = []
    for status in statuses:
        requirement = "required" if status.tool.required else "optional"
        rows.append((
            status.tool.key,
            requirement,
            status.state,
            status.version or "-",
            status.path or "-",
        ))

    headers = ("TOOL", "ROLE", "STATUS", "VERSION", "EXECUTABLE")
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def _show_tools(config: dict, *, check: bool) -> int:
    statuses = all_statuses(config)
    _print_statuses(statuses)
    for status in statuses:
        if status.message:
            print(f"{status.tool.key}: {status.message}")

    if not check:
        return 0

    failed = [
        status
        for status in statuses
        if status.tool.required and status.state != "INSTALLED"
    ]
    if failed:
        print(
            "\nOne or more required tools are missing, unreadable, "
            "or below the configured minimum."
        )
        log_action("dependency check failed")
        return 1
    print("\nAll required tools are available.")
    log_action("dependency check passed")
    return 0


def _config_command(args: argparse.Namespace, config: dict) -> int:
    if args.config_command == "show":
        print(f"Configuration file: {config_path()}")
        print(json.dumps(config, indent=2, sort_keys=True))
        return 0

    if args.config_command == "set-path":
        raw_path = os.path.expandvars(os.path.expanduser(args.path))
        executable = Path(raw_path).resolve()
        if not executable.is_file():
            print(f"That file does not exist: {executable}", file=sys.stderr)
            return 2
        config["paths"][args.tool] = str(executable)
        saved = save_config(config)
        print(f"Saved custom path for {args.tool} in {saved}")
        log_action(f"configured path for {args.tool}")
        return 0

    if args.config_command == "set-min-version":
        if not re.fullmatch(r"v?\d+(?:\.\d+){0,3}", args.version, re.IGNORECASE):
            print("Use a numeric version such as 9.0 or 9.0.1.", file=sys.stderr)
            return 2
        config["minimum_versions"][args.tool] = args.version.lstrip("vV")
        saved = save_config(config)
        print(f"Saved minimum version for {args.tool} in {saved}")
        log_action(f"configured minimum version for {args.tool}")
        return 0

    if args.config_command == "clear-path":
        config["paths"].pop(args.tool, None)
        saved = save_config(config)
        print(f"Removed custom path for {args.tool}. Configuration: {saved}")
        log_action(f"cleared path for {args.tool}")
        return 0

    if args.config_command == "clear-min-version":
        config["minimum_versions"].pop(args.tool, None)
        saved = save_config(config)
        print(f"Removed minimum version for {args.tool}. Configuration: {saved}")
        log_action(f"cleared minimum version for {args.tool}")
        return 0

    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.command == "list":
        return _show_tools(config, check=False)
    if args.command == "check":
        return _show_tools(config, check=True)
    if args.command == "updates":
        return check_updates(config, args.tool)
    if args.command in {"install", "update"}:
        return run_package_action(
            args.tool,
            args.command,
            config,
            dry_run=args.dry_run,
            assume_yes=args.yes,
        )
    if args.command == "config":
        return _config_command(args, config)
    if args.command == "logs":
        if args.lines < 1:
            print("--lines must be at least 1.", file=sys.stderr)
            return 2
        entries = read_log_tail(args.lines)
        if entries:
            print("\n".join(entries))
        else:
            print("No actions have been logged yet.")
        return 0
    return 2
