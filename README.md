# OddWineFixes PoC

> ⚠️ **Proof of Concept Status**: This is an early preview/PoC release. Features and APIs are evolving rapidly. Expect edge cases, and feel free to open issues or PRs!

**OddWineFixes** is an application-agnostic dependency scanner and automator for Wine and Proton on Linux. 

OddWineFixes dynamically inspects an `.exe` file's Portable Executable (PE) headers, cross-references its required DLLs against your Winetricks catalog, and automatically installs missing runtimes into your targeted `WINEPREFIX`.

---

## 🌟 Key Features

* **App-Agnostic & Zero Database Maintenance:** Works for any game, trainer, or Windows application.
* **Smart PE Header Scanning:** Reads the Import Address Table (IAT) directly from `.exe` binaries to detect exact runtime needs (e.g., .NET Framework, Desktop Runtimes, Visual C++ Redistributables, DirectX).
* **Runner Auto-Detection:** Seamlessly handles system `wine`, GE-Proton, Proton-CachyOS, Lutris, and Heroic prefixes without needing custom launcher wrappers.
* **Environment Preserving:** Retains X11/Wayland context and user display variables to prevent zero-CPU hanging issues during process spawning.
* **Iterative Auto-Fix Mode:** Systematically tests missing dependencies and verifies execution success with the user step-by-step.

---

## 📋 Prerequisites

OddWineFixes requires Python 3.11+ and `uv` (or standard `pip`).

System dependencies:
* `wine` / Proton environment installed
* `winetricks`

Python dependencies:
* `pefile`

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/TheOddPirate/oddwinefixes
cd oddwinefixes

```

### 2. Run with `uv` (Recommended)

```bash
uv venv .venv #This creates a virtual env for our dependencies
source .venv/bin/activate.fish #This activates the virtual env, look on the terminal line Activate with: for correct command
uv pip install -r pyproject.toml #installs needed dependencies
uv pip install . #this installs the project in out env
uv run oddwinewfixes #Runs the script

```

---

## 🛠️ How It Works

1. **Path Prompt:** You provide the absolute path to your target `WINEPREFIX` and the `.exe` file you want to launch.
2. **Environment Analysis:** OddWineFixes inspects the prefix's `config_info` (if present) to resolve the matching `wine` and `winetricks` binaries and bin paths.
3. **PE Inspection:** The script scans the target binary's PE Import Address Table (IAT) to identify required external DLLs (ignoring core OS libraries like `kernel32.dll`).
4. **Winetricks Mapping:** It queries the active `winetricks` verb catalog and maps missing DLLs to candidate packages (e.g., `mscoree.dll` -> `dotnetdesktop8`, `vcruntime140.dll` -> `vcrun2015_2022`).
5. **Interactive Testing:** In auto-mode, OddWineFixes installs missing packages one by one and launches the application to confirm if execution succeeded.

---

## 🤝 Contributing

Contributions, feature requests, and bug reports are welcome! Feel free to open an issue or submit a Pull Request.

---

## 📄 License

This project is licensed under **LGPL-2.1-or-later**. Have fun and good luck with this early preview!
