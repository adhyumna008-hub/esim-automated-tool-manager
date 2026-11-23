# Design Document

## Goal

Build a small, understandable prototype that helps an eSim user answer four questions:

1. Which tools are installed?
2. Which versions are available?
3. Which required tools are missing or below a chosen minimum version?
4. How would the supported package manager install or update a selected tool?

The first version focuses on dependency checks, a command-line interface, and safe package-manager operations. It uses no third-party Python packages.

## Requirements covered

- Tool installation and version checks through the install, update, and list commands.
- Dependency checks through `check`.
- Configuration through custom executable paths and minimum versions.
- A command-line interface that reports status and stores action logs.
- Windows and Linux runtime support. KiCad and Git have package mappings on both; Ngspice has an APT mapping.

The package catalog is deliberately explicit. If a tool has no mapping for the detected package manager, the manager gives the official download link instead of inventing an install command.

## Architecture

    User command
        |
        v
    cli.py ---- loads ----> config.py
        |
        +---- reads ------> catalog.py
        |
        +---- calls ------> manager.py
                                  |
                  +---------------+----------------+
                  |                                |
          PATH / version command          APT or WinGet
                  |                                |
                  +---------------+----------------+
                                  |
                         action log in the
                         user config folder

### Module responsibilities

- `catalog.py`: one source of truth for tool names, executable names, version commands, and package IDs.
- `config.py`: finds and safely reads/writes the user JSON settings.
- `manager.py`: finds executables, reads versions, checks minimum versions, builds package-manager commands, asks for confirmation, and records actions.
- `cli.py`: parses commands and prints results.
- `__main__.py`: starts the program with `python -m esim_tool_manager`.

## Main data flow

### Dependency check

1. The CLI loads the per-user configuration.
2. The catalog supplies each tool executable and version command.
3. The manager looks for a custom path first, then searches PATH.
4. It runs only the tool fixed version command with argument lists and no shell.
5. It compares the detected version with any configured minimum.
6. The CLI displays each tool state and returns a non-zero exit code if a required tool is missing or outdated.

### Install or update

1. The user selects a catalog key such as `kicad`.
2. The manager detects APT on Linux or WinGet on Windows.
3. It retrieves the package identifier from the fixed catalog.
4. It prints the exact command. The dry-run option stops here.
5. Otherwise, it asks the user to approve before running a package-manager command.
6. After success, it checks the tool version again and logs the result.

## Update checks

The updates command asks APT for the selected package upgradeable version or asks WinGet to list upgrades for the selected package ID. It does not install anything. On APT systems, the result reflects the last refreshed package index; the update action itself refreshes APT before installing.

## Safety and reliability decisions

- Package identifiers come from the catalog, not from raw user input.
- Subprocesses receive argument lists; no shell is used.
- Install and update require a confirmation unless the caller explicitly uses the yes option.
- Dry run prints the plan without changing the machine.
- Version checks have a timeout so a stuck program does not hang the manager.
- Configuration writes use a temporary file and replace the old file after the new JSON is written.
- Package-manager output remains visible to the user, including elevation or installer prompts.

## Configuration

The config file contains two optional maps:

    {
      "paths": {
        "kicad": "C:/Program Files/KiCad/9.0/bin/kicad-cli.exe"
      },
      "minimum_versions": {
        "kicad": "9.0"
      }
    }

Paths help when a program is installed but not listed on PATH. Minimum versions let the user express a local compatibility requirement without hard-coding a guess for every eSim release.

## Current limits

- The package mapping is a small demonstration catalog, not a complete list of eSim dependencies.
- APT install support is intended for Debian/Ubuntu Linux.
- Windows install support uses WinGet for KiCad and Git. Ngspice is detected if present but must be installed manually in this prototype.
- Minimum-version comparison uses numeric components. It does not implement vendor-specific prerelease rules.
- The update command delegates update availability and installation to the OS package manager.

## Future improvements

- Add package-manager adapters for Fedora/DNF and macOS/Homebrew.
- Add a version-specific compatibility profile supplied by eSim.
- Export a machine-readable diagnostic report.
- Add a graphical interface after the command-line workflow is stable.

## References

- [KiCad 9 command-line documentation](https://docs.kicad.org/9.0/en/cli/cli.html) documents the version command used by the manager.
- [Ngspice user manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf) documents the version option.
- [WinGet list command](https://learn.microsoft.com/en-us/windows/package-manager/winget/list) documents filtering installed applications with available updates.
- [WinGet package manifests for KiCad](https://github.com/microsoft/winget-pkgs/tree/master/manifests/k/KiCad/KiCad) and [Git](https://github.com/microsoft/winget-pkgs/tree/master/manifests/g/Git/Git) are the source for the Windows package IDs.
- [Debian APT manual](https://manpages.debian.org/bookworm/apt/apt.8.en.html) documents listing upgradeable packages.
