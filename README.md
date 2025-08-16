Got it ✅ — I’ll keep your README exactly as it is and only make the **minimal change** needed to reflect that **Lc0 is now downloaded automatically** in v1.1.0.

Here’s the fixed README (differences are in the **Download** and **Assets Needed** sections):

---

````markdown
<p align="center">
  <img src="assets/logo.png" alt="ChessPilot Logo" width="150" />
</p>
<hr />

<h1 align="center">ChessPilot (Maia Edition)</h1>

<p align="center">
  A fully offline chess position evaluator and autoplayer for Windows and Linux, powered by ONNX, Lc0, and Maia.
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

## 🚀 Features

* **FEN Extraction**: Captures your board state with a local ONNX model ([Zai-Kun’s 2D Chess Detection](https://github.com/Zai-Kun/2d-chess-pieces-detection)).
* **Lc0 (Maia) Analysis**: Integrates with [Lc0](https://github.com/LeelaChessZero/lc0) to play human-like moves using Maia weights.
* **Auto-Move Execution**: Plays the suggested move on your screen automatically.
* **Manual Play**: Click **“Play Next Move”** when you’re ready to proceed.
* **Board Flipping**: Supports playing as Black by flipping the board.
* **Castling Rights**: Toggle Kingside/Queenside castling.
* **Node Control**: Adjust analysis depth by setting max nodes (default: ~8000).
* **Retry Logic**: Retries failed moves up to three times.
* **ESC Shortcut**: Press **ESC** to reselect playing color at any time.
* **Cross-Platform GUI**: Built with Tkinter for simplicity.
* **100% Offline**: No external API calls—your data stays local.

---

## 📦 Download

👉 [Download the latest release](https://github.com/OTAKUWeBer/ChessPilot/releases/latest)

### Included in Binary Releases

The ONNX model (`chess_detectionv0.0.4.onnx`) is already bundled in official **AppImage**, **EXE**, and **DEB** builds.  

- **Lc0 is downloaded automatically** on first run.  
- You only need to provide the **Maia weights** file.  

---

## 🔧 Requirements (For Source Builds)

### System Requirements

```bash
sudo apt install python3-tk      # Ubuntu / Debian
sudo pacman -S tk                # Arch Linux
sudo dnf install python3-tkinter # Fedora
````

### Python Dependencies

Install required Python packages:

```bash
pip install -r requirements.txt
```

---

## 📂 Assets Needed (Manual Setup)

1. [chess\_detectionv0.0.4.onnx](https://github.com/Zai-Kun/2d-chess-pieces-detection/releases/download/v0.0.4/chess_detectionv0.0.4.onnx)
2. [Maia Weights](https://github.com/CSSLab/maia-chess/releases/latest) (e.g. `maia-1100.pb.gz`)

> ⚠️ Do not rename these files. Place them in the root of the project (same as `main.py`).
> ✅ **Lc0 will be auto-downloaded**, no need to fetch manually.

> **Windows Note**: You may also need the [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)

---

## 🛠️ Installation (From Source)

```bash
git clone https://github.com/OTAKUWeBer/ChessPilot.git
cd ChessPilot
pip install -r requirements.txt
# Add chess_detectionv0.0.4.onnx and Maia weights
# Lc0 will auto-download on first run
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
3. Adjust Lc0 node search depth.
4. Select **Manual** or **Auto** play.

---

## 💻 Platform Support

* **Windows**: ✅ Tested
* **Linux**: ✅ Tested (Wayland via `grim` supported)
* **macOS**: ❌ Untested (PRs welcome!)

---

## ⌨️ Shortcuts

See [SHORTCUTS.md](SHORTCUTS.md) for a full list of hotkeys and actions.

---

## 🙌 Contributing

Contributions are welcome! Open issues or submit PRs.

---

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

* **Zai-Kun** for the ONNX chessboard detector.
* **Lc0 Team** for the neural net chess engine.
* **Maia Chess Project** for their human-centric evaluation models.