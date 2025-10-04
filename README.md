<p align="center">
  <img src="assets/logo.png" alt="ChessPilot Logo" width="150" />
</p>
<hr />

<h1 align="center">ChessPilot</h1>

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

<br>

---

## 🚀 Features

* **Automatic Stockfish Download**: Automatically detects your CPU and downloads the best Stockfish version—no manual setup required.
* **FEN Extraction**: Captures your board state with a local ONNX model ([Zai-Kun’s 2D Chess Detection](https://github.com/Zai-Kun/2d-chess-pieces-detection)).
* **Stockfish Analysis**: Integrates with the Stockfish engine to compute the optimal move.
* **Auto-Move Execution**: Plays the suggested move on your screen automatically.
* **Manual Play**: Click **“Play Next Move”** when you’re ready to proceed.
* **Board Flipping**: Supports playing as Black by flipping the board.
* **Castling Rights**: Toggle Kingside/Queenside castling.
* **Depth Control**: Adjust analysis depth via a slider (default: 15).
* **Retry Logic**: Retries failed moves up to three times.
* **ESC Shortcut**: Press **ESC** to reselect playing color at any time.
* **Cross-Platform GUI**: Built with Tkinter for simplicity.
* **100% Offline**: No external API calls—your data stays local.

---

## 📦 Download

👉 [Download the latest release](https://github.com/OTAKUWeBer/ChessPilot/releases/latest)

### Included in Binary Releases

The ONNX model (`chess_detectionv0.0.4.onnx`) is already bundled in official **AppImage**, **EXE**, and **DEB** builds.
Stockfish will be **downloaded automatically** on first run according to your CPU.

---

## 🔧 Engine Configuration (v1.0.1)

You can fine-tune Stockfish’s performance without touching any code.
Simply place an `engine_config.txt` file next to the ChessPilot executable:

```ini
# ================================
# ChessPilot Engine Configuration
# ================================
# Memory used in MB (64–1024+ recommended)
setoption name Hash value 512

# CPU threads to use (1–8; match your CPU core count)
setoption name Threads value 2
```

1. Edit `Hash` to adjust how much RAM (in MB) Stockfish uses.
2. Edit `Threads` to match your CPU cores.
3. Save and restart ChessPilot to apply the new settings.

---

## ⚙️ Prerequisites (For Source Builds / Raw File Users)

If you're running from source or using the **raw files** (not packaged AppImage/EXE/DEB), you need:

```bash
sudo apt install python3-tk      # Ubuntu / Debian
sudo pacman -S tk                # Arch Linux
sudo dnf install python3-tkinter # Fedora
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

* **Assets Needed (Source only)**:

  1. [chess\_detectionv0.0.4.onnx](https://github.com/Zai-Kun/2d-chess-pieces-detection/releases/download/v0.0.4/chess_detectionv0.0.4.onnx)

> Stockfish will be downloaded automatically when you run ChessPilot.

> **Windows Raw File Users Only**: You may also need the Microsoft Visual C++ Redistributable if it's not already installed.
> [Download here](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)

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

**Workflow**:

1. Choose **White** or **Black**.
2. Enable castling rights if needed.
3. Adjust analysis depth.
4. Select **Manual** or **Auto** play.

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

Contributions are welcome! Please open an issue or submit a pull request.

---

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

* **Zai-Kun** for the ONNX chess piece detector.
* **Stockfish Team** for the world’s strongest open-source engine.