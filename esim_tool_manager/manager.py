from __future__ import annotations

import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .catalog import TOOLS, ToolSpec, get_tool
from .config import config_dir


VERSION_PATTERN = re.compile(r"(?<!\d)v?(\d+(?:\.\d+){0,3})", re.IGNORECASE)


@dataclass(frozen=True)
class ToolStatus:
    tool: ToolSpec
    state: str
    version: str | None
    path: str | None
    minimum_version: str | None = None
    message: str = ""


@dataclass(frozen=True)
class PackageManager:
    kind: str
    executable: str
    name: str


def _version_tuple(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", value)
    return tuple(int(number) for number in numbers[:4])


def version_is_at_least(current: str, minimum: str) -> bool:
    left = _version_tuple(current)
    right = _version_tuple(minimum)
    width = max(len(left), len(right))
    left += (0,) * (width - len(left))
    right += (0,) * (width - len(right))
    return left >= right


def _extract_version(output: str) -> str | None:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    lines.sort(
        key=lambda line: not any(
            marker in line.lower() for marker in ("kicad", "ngspice", "git", "version")
        )
    )
    for line in lines:
        match = VERSION_PATTERN.search(line)
        if match:
            return match.group(1)
    return None


def inspect_tool(tool: ToolSpec, config: dict[str, Any]) -> ToolStatus:
    minimum = config.get("minimum_versions", {}).get(tool.key)
    configured_path = config.get("paths", {}).get(tool.key)

    if configured_path:
        expanded = os.path.expandvars(os.path.expanduser(configured_path))
        candidate = Path(expanded)
        if not candidate.is_file():
            return ToolStatus(
                tool, "BAD PATH", None, str(candidate), minimum,
                "The configured executable path does not exist.",
            )
        executable = str(candidate)
    else:
        executable = shutil.which(tool.executable)

    if not executable:
        return ToolStatus(
            tool, "MISSING", None, None, minimum, "Executable was not found on PATH."
        )

    try:
        result = subprocess.run(
            [executable, *tool.version_args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ToolStatus(
            tool, "VERSION ERROR", None, executable, minimum,
            "The version command took longer than 10 seconds.",
        )
    except OSError as exc:
        return ToolStatus(
            tool, "VERSION ERROR", None, executable, minimum, str(exc)
        )

    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if result.returncode != 0:
        detail = output.strip().splitlines()
        message = detail[0][:160] if detail else f"Exit code {result.returncode}."
        return ToolStatus(
            tool, "VERSION ERROR", None, executable, minimum, message
        )

    version = _extract_version(output)
    if not version:
        return ToolStatus(
            tool, "UNKNOWN VERSION", None, executable, minimum,
            "The program ran, but its version output was not recognized.",
        )

    if minimum and not version_is_at_least(version, minimum):
        return ToolStatus(
            tool, "OUTDATED", version, executable, minimum,
            f"Configured minimum version is {minimum}.",
        )
    return ToolStatus(tool, "INSTALLED", version, executable, minimum)


def detect_package_manager() -> PackageManager | None:
    system = platform.system()
    if system == "Windows":
        executable = shutil.which("winget")
        if executable:
            return PackageManager("winget", executable, "WinGet")
    elif system == "Linux":
        executable = shutil.which("apt-get")
        if executable:
            return PackageManager("apt", executable, "APT")
    return None


def _apt_prefix() -> list[str] | None:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return []
    sudo = shutil.which("sudo")
    return [sudo] if sudo else None


def package_commands(
    tool: ToolSpec, action: str
) -> tuple[PackageManager | None, list[list[str]] | None, str | None]:
    manager = detect_package_manager()
    if not manager:
        return None, None, "No supported package manager was found (APT or WinGet)."

    package = tool.packages.get(manager.kind)
    if not package:
        return (
            manager,
            None,
            f"{tool.name} has no automatic {manager.name} package mapping. "
            f"Install it manually: {tool.install_url}",
        )

    if manager.kind == "apt":
        prefix = _apt_prefix()
        if prefix is None:
            return manager, None, "APT needs root access; install sudo or run as root."
        commands = [
            [*prefix, manager.executable, "update"],
            [
                *prefix,
                manager.executable,
                "install",
                "-y",
                *(["--only-upgrade"] if action == "update" else []),
                package,
            ],
        ]
    else:
        verb = "upgrade" if action == "update" else "install"
        commands = [[
            manager.executable,
            verb,
            "--id",
            package,
            "--exact",
            "--source",
            "winget",
        ]]
    return manager, commands, None


def format_command(command: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def log_action(message: str) -> None:
    try:
        directory = config_dir()
        directory.mkdir(parents=True, exist_ok=True)
        log_file = directory / "actions.log"
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with log_file.open("a", encoding="utf-8") as stream:
            stream.write(f"{timestamp} {message}\n")
    except OSError as exc:
        print(f"Warning: could not write the action log: {exc}", file=sys.stderr)


def read_log_tail(lines: int = 20) -> list[str]:
    path = config_dir() / "actions.log"
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]


def run_package_action(
    tool_key: str,
    action: str,
    config: dict[str, Any],
    *,
    dry_run: bool = False,
    assume_yes: bool = False,
) -> int:
    tool = get_tool(tool_key)
    current = inspect_tool(tool, config)

    if action == "install" and current.state == "INSTALLED" and not dry_run:
        print(f"{tool.name} is already installed ({current.version}).")
        return 0
    if action == "update" and current.state not in {"INSTALLED", "OUTDATED"}:
        print(f"Cannot update {tool.name}: its executable is not available.")
        return 1

    manager, commands, error = package_commands(tool, action)
    if error or commands is None:
        print(error or "Could not create an installation plan.")
        log_action(f"{action} {tool.key}: unavailable ({error})")
        return 1

    print(f"{action.title()} plan for {tool.name} using {manager.name}:")
    for command in commands:
        print(f"  {format_command(command)}")
    if dry_run:
        print("Dry run only; nothing was installed or changed.")
        log_action(f"dry-run {action} {tool.key}")
        return 0

    if not assume_yes:
        try:
            answer = input("Run these commands? [y/N] ").strip().lower()
        except EOFError:
            answer = ""
        if answer not in {"y", "yes"}:
            print("Cancelled. No package-manager command was run.")
            log_action(f"cancelled {action} {tool.key}")
            return 0

    log_action(f"started {action} {tool.key} via {manager.name}")
    for command in commands:
        try:
            result = subprocess.run(command, timeout=1800, check=False)
        except subprocess.TimeoutExpired:
            print("The package-manager command timed out after 30 minutes.")
            log_action(f"failed {action} {tool.key}: timeout")
            return 1
        except OSError as exc:
            print(f"Could not run the package manager: {exc}")
            log_action(f"failed {action} {tool.key}: {exc}")
            return 1
        if result.returncode != 0:
            print(f"Package manager exited with code {result.returncode}.")
            log_action(f"failed {action} {tool.key}: exit {result.returncode}")
            return result.returncode or 1

    updated = inspect_tool(tool, config)
    print(f"Finished. Current status: {updated.state}; version: {updated.version or '-'}")
    log_action(
        f"finished {action} {tool.key}: {updated.state} "
        f"version={updated.version or 'unknown'}"
    )
    return 0 if updated.state == "INSTALLED" else 1


def check_updates(config: dict[str, Any], tool_key: str | None = None) -> int:
    manager = detect_package_manager()
    if not manager:
        print("No supported package manager was found (APT or WinGet).")
        return 1

    selected = [get_tool(tool_key)] if tool_key else list(TOOLS.values())
    failures = 0
    for tool in selected:
        package = tool.packages.get(manager.kind)
        if not package:
            print(f"{tool.name}: no automatic {manager.name} package mapping.")
            continue

        status = inspect_tool(tool, config)
        if status.state not in {"INSTALLED", "OUTDATED"}:
            print(f"{tool.name}: not installed or its version could not be checked.")
            continue

        if manager.kind == "apt":
            apt = shutil.which("apt")
            if not apt:
                print("APT list command is unavailable; cannot check updates.")
                failures += 1
                continue
            command = [apt, "list", "--upgradable", package]
        else:
            command = [
                manager.executable,
                "list",
                "--id",
                package,
                "--exact",
                "--upgrade-available",
            ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"{tool.name}: update check failed: {exc}")
            log_action(f"update check failed for {tool.key}: {exc}")
            failures += 1
            continue

        output = "\n".join(
            part for part in (result.stdout, result.stderr) if part
        )
        if result.returncode != 0:
            print(f"{tool.name}: update check failed with exit code {result.returncode}.")
            if output.strip():
                print(output.strip())
            log_action(f"update check failed for {tool.key}: exit {result.returncode}")
            failures += 1
            continue

        lines = output.splitlines()
        if manager.kind == "apt":
            matches = [
                line for line in lines
                if line.lower().startswith(package.lower() + "/")
                and "upgradable from:" in line.lower()
            ]
        else:
            matches = [
                line for line in lines
                if package.casefold() in line.casefold()
                and not line.strip().lower().startswith(
                    ("name", "no installed", "no applicable")
                )
            ]

        if matches:
            print(f"{tool.name}: update available")
            print("\n".join(matches))
            log_action(f"update available for {tool.key}")
        else:
            print(f"{tool.name}: no update listed by {manager.name}")
            log_action(f"no update listed for {tool.key}")
    return 1 if failures else 0


def all_statuses(config: dict[str, Any]) -> list[ToolStatus]:
    return [inspect_tool(tool, config) for tool in TOOLS.values()]
