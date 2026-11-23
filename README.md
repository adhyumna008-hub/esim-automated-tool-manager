# eSim Tool Manager

A small Python command-line prototype for finding, checking, installing, and updating external tools used with eSim.

It uses only Python standard-library modules. The read-only commands do not install anything. Install and update commands show the planned system command and ask before running it.

## What this prototype covers

| Task requirement | What the prototype does |
| --- | --- |
| Tool installation | Installs KiCad and Git with APT or WinGet; installs Ngspice with APT. |
| Updates | Runs the matching package manager update/upgrade command for a selected tool. |
| Configuration | Saves custom executable paths and minimum versions in a per-user JSON file. |
| Dependency checker | Checks KiCad and Ngspice as required tools, and Git as optional. |
| User interface | Provides commands to list, check, install, update, configure, and view action logs. |
| Cross-platform | Runs on Windows and Linux. KiCad and Git installation are mapped for both; Ngspice auto-install is mapped for APT. |

The package catalog is intentionally small. When an automatic installer is unavailable, the manager prints the official download page instead of guessing a package name.

## Quick start

You need Python 3.10 or newer. No extra Python packages are required.

From this folder, show the available commands:

    python -m esim_tool_manager --help

See installed tools and their versions:

    python -m esim_tool_manager list

Check required dependencies:

    python -m esim_tool_manager check

Preview an installation without changing the computer:

    python -m esim_tool_manager install kicad --dry-run

Run an installation after reviewing the command:

    python -m esim_tool_manager install kicad

The install command asks for confirmation. On Linux, APT may ask for your system password through sudo. On Windows, WinGet may show its own installer prompts. The manager leaves those prompts visible.

The updates command reads the package-manager update list. APT uses its existing package index, so refresh that index first if you need current results.

## Commands

    python -m esim_tool_manager list
    python -m esim_tool_manager check
    python -m esim_tool_manager updates [TOOL]
    python -m esim_tool_manager install TOOL [--dry-run] [--yes]
    python -m esim_tool_manager update TOOL [--dry-run] [--yes]
    python -m esim_tool_manager config show
    python -m esim_tool_manager config set-path TOOL FULL_PATH
    python -m esim_tool_manager config set-min-version TOOL VERSION
    python -m esim_tool_manager config clear-path TOOL
    python -m esim_tool_manager config clear-min-version TOOL
    python -m esim_tool_manager logs [--lines N]

Supported tool keys are **kicad**, **ngspice**, and **git**.

For example, if KiCad is installed but its command is not on PATH:

    python -m esim_tool_manager config set-path kicad "C:/Program Files/KiCad/9.0/bin/kicad-cli.exe"
    python -m esim_tool_manager config set-min-version kicad 9.0
    python -m esim_tool_manager check

The configuration and action log are saved in your user profile:

- Windows: `%APPDATA%/esim-tool-manager`
- Linux: `$XDG_CONFIG_HOME/esim-tool-manager`, or `~/.config/esim-tool-manager`

## How to run on Windows

Open PowerShell, change to this project folder, then run:

    py -3 -m esim_tool_manager list
    py -3 -m esim_tool_manager install kicad --dry-run

WinGet is used for KiCad and Git when it is available. Ngspice can still be detected using a custom path, but this prototype does not guess a WinGet package for it.

## How to run on Linux

Open a terminal in this project folder, then run:

    python3 -m esim_tool_manager list
    python3 -m esim_tool_manager install ngspice --dry-run

APT is used on Debian/Ubuntu systems. Other Linux distributions can use `config set-path` for detection; their package-manager install commands are outside this prototype scope.

## Design and learning

- [DESIGN.md](DESIGN.md) explains the architecture and its decisions.
- [LEARNING_GUIDE.md](LEARNING_GUIDE.md) walks through the code in beginner-friendly order.

## Submission checklist

1. Create a private GitHub repository and upload this project.
2. Give repository access to **Eyantra698Sumanto**.
3. Email the repository link and report to **contact-esim@fossee.in**.
4. Use the subject line: **eSim Semester Long Internship - Autumn 2026 Submission Task 5**.

The optional presentation can show `list`, `check`, a dry-run install plan, and a real installation only if you choose to approve it.
