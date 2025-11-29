<p align="center">
  <img src="assets/logo.png" alt="ChessPilot Logo" width="150" />
</p>
<hr />

# ChessPilot — v2.0.0

<p align="center">
  A fully offline chess position evaluator and autoplayer for Windows and Linux, powered by ONNX and Stockfish.
</p>

<p align="center">
<a href="https://img.shields.io/github/license/OTAKUWeBer/ChessPilot?style=for-the-badge"><img src="https://img.shields.io/github/license/OTAKUWeBer/ChessPilot?style=for-the-badge&color=F48041"></a>
<a href="https://img.shields.io/github/v/release/OTAKUWeBer/ChessPilot?style=for-the-badge"><img src="https://img.shields.io/github/v/release/OTAKUWeBer/ChessPilot?style=for-the-badge&color=0E80C0"></a>
<a href="https://img.shields.io/codefactor/grade/github/OTAKUWeBer/ChessPilot?style=for-the-badge&color=03A363"><img src="https://img.shields.io/codefactor/grade/github/OTAKUWeBer/ChessPilot?style=for-the-badge&color=03A363"></a>
<a href="https://img.shields.io/github/downloads/OTAKUWeBer/ChessPilot/total.svg?style=for-the-badge"><img src="https://img.shields.io/github/downloads/OTAKUWeBer/ChessPilot/total.svg?style=for-the-badge&color=CAF979"></a>
<a href="https://img.shields.io/github/issues/OTAKUWeBer/ChessPilot?style=for-the-badge"><img src="https://img.shields.io/github/issues/OTAKUWeBer/ChessPilot?style=for-the-badge&color=CE5842"></a>
<br>
<a href="https://img.shields.io/badge/Made_For-Linux-FCC624?style=for-the-badge&logo=linux&logoColor=white"><img src="https://img.shields.io/badge/Made_For-Linux-FCC624?style=for-the-badge&logo=linux&logoColor=white"></a>
<a href="https://img.shields.io/badge/Made_For-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white"><img src="https://img.shields.io/badge/Made_For-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white"></a>

---

## 🚀 What's new in v2.0.0 — PyQt6 UI (minor, polished)

This release advances the project to **v2.0.0** and keeps the previously introduced PyQt6 frontend while remaining intentionally minimal in behavioral changes. The core functionality is unchanged; the update focuses on a more polished, stable PyQt6 experience and small fixes under the hood.

Highlights:

* ✅ **Version bumped to v2.0.0**.
* ✅ **PyQt6 GUI** (continued — replaces Tkinter) — improved stability and polish.
* ✅ No workflow changes: FEN extraction, Stockfish analysis, auto-move execution, board flipping, castling toggles, depth control, retry logic, and ESC shortcut remain the same.
* ⚠️ Source-build users: ensure PyQt6 is installed (see prerequisites).

---

## 🚀 What's new in v2.1.0 — Stability, Precision & Performance (minimal, refined)

This update delivers targeted refinements that enhance reliability across all supported platforms while preserving the exact workflow introduced in v2.0.0. No features, behaviors, or UI flows have been altered — only improved.

### **Highlights (v2.1.0)**

* **Pawn Promotion, Fully Supported**
  Pawns can now promote to any piece Stockfish chooses, with smooth, precise selection. Works flawlessly across all board themes and animations, making promotions faster and more reliable than ever.

---

## 🚀 Features

* **Automatic Stockfish Download**: Detects your CPU and downloads the best Stockfish build automatically.
* **FEN Extraction**: Local ONNX model ([Zai-Kun’s 2D Chess Detection](https://github.com/Zai-Kun/2d-chess-pieces-detection)).
* **Stockfish Analysis**: Integrates Stockfish for optimal move suggestions.
* **Auto-Move Execution**: Plays the chosen move on your screen automatically.
* **Manual Play**: Click **“Play Next Move”** when you want to proceed manually.
* **Board Flipping**: Play as Black by flipping the board.
* **Castling Rights**: Toggle Kingside/Queenside castling.
* **Depth Control**: Slider to adjust analysis depth (default: 15).
* **Retry Logic**: Retries failed moves up to three times.
* **ESC Shortcut**: Press **ESC** to reselect playing color at any time.
* **Cross-Platform GUI**: Built with **PyQt6** for a modern desktop UI.
* **100% Offline**: No external API calls — all processing stays local.

---

## 📦 Download

👉 [Download the latest release](https://github.com/OTAKUWeBer/ChessPilot/releases/latest)

> The ONNX model (`chess_detectionv0.0.4.onnx`) is bundled in official **AppImage**, **EXE**, and **DEB** builds. Stockfish will be downloaded automatically on first run.

---

## 🔧 Engine Configuration (v1.0.1)

You can fine-tune Stockfish’s performance using an `engine_config.txt` file next to the ChessPilot executable:

```ini
# ================================
# ChessPilot Engine Configuration
# ================================
# Memory used in MB (64–1024+ recommended)
setoption name Hash value 512

# CPU threads to use (1–8; match your CPU core count)
setoption name Threads value 2
```

1. Edit `Hash` to adjust RAM (in MB) Stockfish uses.
2. Edit `Threads` to match your CPU cores.
3. Save and restart ChessPilot to apply settings.

---

## ⚙️ Prerequisites (For Source Builds / Raw File Users)

**PyQt6 is required when running from source.**

### Linux

```bash
# system packages (examples — adapt to your distro)
sudo apt install python3-pyqt6        # Ubuntu / Debian
sudo pacman -S python-pyqt6           # Arch Linux
sudo dnf install python3-qt6          # Fedora (package name may vary)
```

### Windows

Install PyQt6 via pip in your virtualenv:

```bash
pip install PyQt6
```

### General (Python packages)

```bash
pip install -r requirements.txt
```

**Assets Needed (Source only)**:

* `chess_detectionv0.0.4.onnx` — included in binaries; if running from raw files, download from the detector release.

> **Windows Raw File Users Only**: You may still need the Microsoft Visual C++ Redistributable if not already installed. [Microsoft VC++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)

---

## 🛠️ Installation (From Source)

```bash
git clone https://github.com/OTAKUWeBer/ChessPilot.git
cd ChessPilot
pip install -r requirements.txt
# Add ONNX model if not using binary
```

---

## ▶️ Usage

From the project root:

```bash
python src/main.py
```

Workflow:

1. Choose **White** or **Black**.
2. Enable castling rights if needed.
3. Adjust analysis depth.
4. Select **Manual** or **Auto** play.

(Behavior and shortcuts are unchanged — ESC still reopens color selection.)

---

## 💻 Platform Support

* **Windows**: ✅ Tested
* **Linux**: ✅ Tested (including Wayland via `grim`)
* **macOS**: ❌ Untested (no macOS build; contributions welcome!)

---

## ⌨️ Shortcuts

See [SHORTCUTS.md](SHORTCUTS.md) for a full list of hotkeys and actions.

---

## 🤝 Contributing

Contributions welcome! Open an issue or submit a pull request. If you'd like to help port or test macOS builds, let us know.

---

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

* **Zai-Kun** for the ONNX chess piece detector.
* **Stockfish Team** for the world’s strongest open-source engine.