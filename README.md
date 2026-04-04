<p align="center">
  <img src="assets/logo.png" alt="ChessPilot Logo" width="150" />
</p>
<hr />

# ChessPilot — v2.x

**A fully offline chess position evaluator and autoplayer for Windows and Linux — powered by ONNX and Stockfish.**

<p align="center">
<a href="https://img.shields.io/github/license/OTAKUWeBer/ChessPilot?style=for-the-badge"><img src="https://img.shields.io/github/license/OTAKUWeBer/ChessPilot?style=for-the-badge&color=F48041"></a>
<a href="https://img.shields.io/github/v/release/OTAKUWeBer/ChessPilot?style=for-the-badge"><img src="https://img.shields.io/github/v/release/OTAKUWeBer/ChessPilot?style=for-the-badge&color=0E80C0"></a>
<a href="https://img.shields.io/codefactor/grade/github/OTAKUWeBer/ChessPilot?style=for-the-badge&color=03A363"><img src="https://img.shields.io/codefactor/grade/github/OTAKUWeBer/ChessPilot?style=for-the-badge&color=03A363"></a>
<a href="https://img.shields.io/github/downloads/OTAKUWeBer/ChessPilot/total.svg?style=for-the-badge"><img src="https://img.shields.io/github/downloads/OTAKUWeBer/ChessPilot/total.svg?style=for-the-badge&color=CAF979"></a>
<a href="https://img.shields.io/github/issues/OTAKUWeBer/ChessPilot?style=for-the-badge"><img src="https://img.shields.io/github/issues/OTAKUWeBer/ChessPilot?style=for-the-badge&color=CE5842"></a>
<br>
<a href="https://img.shields.io/badge/Made_For-Linux-FCC624?style=for-the-badge&logo=linux&logoColor=white"><img src="https://img.shields.io/badge/Made_For-Linux-FCC624?style=for-the-badge&logo=linux&logoColor=white"></a>
<a href="https://img.shields.io/badge/Made_For-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white"><img src="https://img.shields.io/badge/Made_For-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white"></a>

<p align="center">
  A lightweight, privacy-first tool that reads a **2D on-screen chess board** (Chess.com, Lichess, WorldChess, etc.), evaluates the position locally with Stockfish, and (optionally) plays the best move automatically.
</p>

---

# 🎥 Demo Video

<p align="center">
  <img src="assets/demo.gif" width="600" />
</p>

---

## 🎉 Highlights (What's New)

### **v2.2.0 — The Architecture & Aesthetics Update**

* **Massive Structural Refactor** — The monolithic executor module has been split into clean `core`, `game`, and `utils` domains, improving performance and maintainability.
* **Bulletproof Engine Stability** — Prevented Stockfish from hanging infinitely (the "stuck analyzing" bug) by adding precise timeouts, and added safe `Ctrl+C` interrupt handlers to end the process cleanly without core dumping.
* **Gorgeous UI Modernization** — Replaced mismatched styles with a cohesive "Emerald and Slate" dark theme managed through a centralized Styles class.
* **Linux Patches** — Fixed Wayland cursor tracking and pawn promotion screenshot captures.

### **v2.1.0 — Stability, Precision & Performance**

* Full pawn promotion support — handled automatically and reliably.
* Small under-the-hood improvements for cross-platform stability.

### **v2.0.0 — PyQt6 UI (Polished)**

* Brand-new PyQt6-based frontend (replaces old Tkinter UI).
* Same workflow and shortcuts — just smoother and more stable.

---

## ⚡ Features

* **100% Offline** — all detection & analysis run locally.
* **Automatic Stockfish Download (CPU-Optimized)** — ChessPilot automatically detects your CPU features (AVX2, AVX512, POPCNT, etc.) and downloads the most optimized Stockfish build on first run.
* **FEN Extraction** — ONNX-based piece detector (Zai-Kun’s model).
* **Stockfish Analysis** — instant best-move suggestions.
* **Auto Move Execution** — applies engine moves to the GUI board.
* **Manual Play** — use **Play Next Move** to control timing.
* **Automatic Promotion** — follows Stockfish’s preferred choice.
* **Castling Rights & Depth Control** — flexible configuration.
* **Retry Logic** — failed moves automatically retried up to 3 times.
* **Cross-Platform** — AppImage/DEB for Linux, EXE for Windows.

---

## 📦 Download

👉 **[Download the latest release](https://github.com/OTAKUWeBer/ChessPilot/releases/latest)**

The ONNX model (`chess_detectionv0.0.4.onnx`) is included inside all official AppImage, EXE, and DEB builds.

---

## 🔒 Windows Antivirus Warnings (False Positives)

Windows may flag unsigned executables — this is common for small open-source projects.

**If you see a warning:**

1. **Verify the release** on GitHub.
2. **Scan the binary** on VirusTotal.
3. **Build from source** (`python src/main.py`) for maximum safety.
4. **Only run if comfortable** — or use a VM.

---

## ⚙️ Prerequisites (From Source)

PyQt6 is required for the UI.

### **Related Links**

* ONNX Model: [https://github.com/Zai-Kun/2d-chess-pieces-detection](https://github.com/Zai-Kun/2d-chess-pieces-detection/releases/latest)
* VC++ Redistributable (Windows): [https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
* Stockfish Engine: [https://stockfishchess.org/](https://stockfishchess.org/)

---

### Linux

Install system dependencies:

```bash
# Ubuntu / Debian
sudo apt install python3-pyqt6        

# Arch Linux
sudo pacman -S python-pyqt6

# Fedora
sudo dnf install python3-qt6
```

**Wayland Users (Arch Linux only)**

If you are running Wayland instead of X11, install the following:

```bash
sudo pacman -S wayland-utils
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

> Make sure your Python virtual environment is activated if you are using one.

### Windows

```bash
pip install -r requirements.txt
```

If you see errors about missing `vcruntime` or `msvcp` DLLs, install the **latest VC++ Redistributable** - [here](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

---

## ▶️ Run (From Source)

```bash
git clone https://github.com/OTAKUWeBer/ChessPilot.git
cd ChessPilot
pip install -r requirements.txt
python src/main.py
```

### **Workflow**

1. Choose **White** or **Black**.
2. Set castling rights if needed.
3. Adjust analysis depth.
4. Pick **Manual** or **Auto** mode.
5. (Press **ESC** to reopen color selection.)

---

## ✅ Platform Support

* **Windows** — tested, EXE provided
* **Linux** — tested, AppImage & DEB provided (Wayland supported)
* **macOS** — not yet supported (looking for contributors)

---

## 🔁 Troubleshooting & FAQ

**Board detection is incorrect**
→ Move the ChessPilot UI aside so the detector has a clear view of the board.

**Stockfish didn’t download**
→ Check your internet connection and firewall settings.
→ Alternatively, manually place a Stockfish ZIP or binary in the `src/` folder.

---

## 🤝 Contributing

PRs and issues are welcome.

Areas that need help:

* macOS packaging
* UI/UX enhancements

---

## 📜 License

This project is under the **MIT License**.

---

## 🙏 Acknowledgments

**Project & Dependencies**

* Zai-Kun — ONNX 2D chess piece detector
* Stockfish Team — world-class chess engine
* Microsoft VC++ Runtime
* All contributors and testers