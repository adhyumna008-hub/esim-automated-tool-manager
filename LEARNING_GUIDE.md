# Learning Guide

This guide follows the order a Python developer can use to understand the project. You can run each command as you read.

## 1. Start with the catalog

Open `esim_tool_manager/catalog.py`.

Each `ToolSpec` is a small record describing one program:

- Its public key, such as `kicad`.
- The executable the computer should search for, such as `kicad-cli`.
- The arguments that ask the program for its version.
- Package identifiers for supported package managers.
- Whether the tool is required by this prototype.

This is configuration as data: adding a supported tool starts by adding one catalog entry instead of scattering names through the program.

## 2. Understand PATH and executable discovery

Open `esim_tool_manager/manager.py` and find `inspect_tool`.

`shutil.which` searches PATH, the list of folders where command-line programs are usually installed. If a program is in a different folder, the user can save its full path with `config set-path`.

The manager then uses `subprocess.run` to ask the tool for its version. It passes a list of arguments. That avoids asking a command shell to reinterpret the text.

## 3. Follow a dependency check

Run:

    python -m esim_tool_manager check

Then trace `_show_tools` in `cli.py`:

1. `all_statuses` checks each catalog entry.
2. `_print_statuses` formats a simple table.
3. Required tools that are missing or too old make the command return exit code 1.

Exit codes are useful because another program or a CI job can detect whether the environment is ready.

## 4. Follow an install plan without installing anything

Run:

    python -m esim_tool_manager install kicad --dry-run

`package_commands` turns the catalog package identifier into a list of arguments. The CLI prints the plan and exits before invoking the package manager.

Remove the dry-run option only when you are ready to install. The program then asks for a separate yes/no confirmation.

## 5. Check updates without installing

Run:

    python -m esim_tool_manager updates
    python -m esim_tool_manager updates kicad

This asks the operating-system package manager whether a supported tool has an update. The command only reads update information. APT uses its existing package index, while WinGet returns its own update listing.

## 6. Learn configuration and JSON

Run:

    python -m esim_tool_manager config show

Custom paths and minimum versions are saved as JSON in your user config folder. `config.py` handles that file so the other modules do not need to know where Windows or Linux stores settings.

Try:

    python -m esim_tool_manager config set-min-version kicad 9.0
    python -m esim_tool_manager check
    python -m esim_tool_manager config clear-min-version kicad

## 7. Read the CLI last

Open `esim_tool_manager/cli.py`.

`argparse` defines the commands and their arguments. Each command calls a small function from `manager.py` or `config.py`, then displays a result. Keeping command parsing separate from tool discovery makes the code easier to change.

## A practice exercise

Add another tool to the catalog:

1. Find its command name and version command.
2. Find a trustworthy package identifier for a supported package manager.
3. Add one `ToolSpec`.
4. Run `list` and `check`.
5. Review `install TOOL --dry-run` before attempting a real install.

Do not add a package identifier from memory. Verify it in the package manager official catalog first.

## Concepts used

- Dataclasses: simple structured records for tools and detected status.
- Type hints: make function inputs and outputs easier to understand.
- `pathlib`: work with file paths without hand-building path separators.
- `argparse`: create a command-line interface using the Python standard library.
- `subprocess`: communicate with external programs.
- JSON: store a small user-specific configuration.
- Defensive error handling: show missing tools, invalid paths, timeouts, and failed installs clearly.
