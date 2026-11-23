from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ToolSpec:
    key: str
    name: str
    executable: str
    version_args: tuple[str, ...]
    packages: Mapping[str, str]
    required: bool
    install_url: str
    purpose: str


TOOLS: dict[str, ToolSpec] = {
    "kicad": ToolSpec(
        key="kicad",
        name="KiCad CLI",
        executable="kicad-cli",
        version_args=("version",),
        packages={"apt": "kicad", "winget": "KiCad.KiCad"},
        required=True,
        install_url="https://www.kicad.org/download/",
        purpose="Schematic, PCB, and electronics design tools.",
    ),
    "ngspice": ToolSpec(
        key="ngspice",
        name="Ngspice",
        executable="ngspice",
        version_args=("--version",),
        packages={"apt": "ngspice"},
        required=True,
        install_url="https://ngspice.sourceforge.io/download.html",
        purpose="Circuit simulation engine.",
    ),
    "git": ToolSpec(
        key="git",
        name="Git",
        executable="git",
        version_args=("--version",),
        packages={"apt": "git", "winget": "Git.Git"},
        required=False,
        install_url="https://git-scm.com/downloads",
        purpose="Source control for eSim development and task submissions.",
    ),
}


def get_tool(key: str) -> ToolSpec:
    try:
        return TOOLS[key]
    except KeyError as exc:
        available = ", ".join(TOOLS)
        raise ValueError(f"Unknown tool {key!r}. Choose from: {available}") from exc
