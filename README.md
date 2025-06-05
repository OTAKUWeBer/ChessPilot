# Chess Position Evaluator

<p align="center">
  <img src="assets/chess-banner.jpg" alt="Chess Banner" width="600" />
</p>

## Features

* **FEN Extraction**: Detects the board position from your screen using [Zai-Kun's Chess Pieces Detection](https://github.com/Zai-Kun/2d-chess-pieces-detection).
* **Local Model Inference**: Uses a local ONNX model to ensure fast, offline board recognition.
* **Stockfish Integration**: Analyzes the board and suggests the best move using the Stockfish chess engine.
* **Auto Move Execution**: Automatically plays the best move on your screen.
* **Manual Play**: Use a **"Play Next Move"** button to control when the move is made.
* **Board Flipping**: Automatically flips the board if you're playing as Black.
* **Castling Support**: Tick checkboxes to indicate castling rights before each move.
* **Depth Control**: A slider lets you set Stockfish’s analysis depth (default: 15).
* **Retry Mechanism**: Retries the move up to 3 times if it doesn't execute correctly.
* **ESC Key Functionality**: Press ESC to reselect playing color.
* **GUI Interface**: Uses Tkinter for a user-friendly, interactive experience.
* **Performance Optimized**: All processing is done locally—no external API calls.

---

## Download

Get the latest release from [GitHub Releases](https://github.com/OTAKUWeBer/ChessPilot/releases/latest/).

### Required Downloads (Place These in the Project Folder)

1. **Chess Detection Model**
   Download the ONNX model from:
   [Download ONNX Model](https://github.com/Zai-Kun/2d-chess-pieces-detection/releases/download/v0.0.4/chess_detectionv0.0.4.onnx)

   > ⚙️ **Note:** The ONNX runtime may require the Microsoft Visual C++ Redistributable on Windows. Download the latest supported version from the official Microsoft site: [Visual C++ Redistributable Downloads](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)

2. **Stockfish Engine**
   Download a Stockfish ZIP file from the official site:
   [Download Stockfish ZIP](https://stockfishchess.org/download/)

> 🗂️ **Important:** Do **not** rename the files. Just place both the ONNX file and Stockfish ZIP directly inside the `ChessPilot` directory (same folder as `main.py`). The script will automatically handle extraction and detection.

---

## Prerequisites

Make sure you have:

- **Python 3.10+**
- **Python Packages**:
  - `mss`
  - `Pillow`
  - `pyautogui`
  - `pywin32`
  - `onnxruntime`
  - `numpy`
  - `colorama`
  - `tkinter`

### Installing Dependencies

```bash
pip install -r requirements.txt
````

### If `tkinter` is Missing

Tkinter is usually bundled with Python on Windows and macOS, but if you're on Linux or using a minimal Python build, you may need to install it manually:

* **Ubuntu / Debian:**

  ```bash
  sudo apt install python3-tk
  ```

* **Arch Linux:**

  ```bash
  sudo pacman -S tk
  ```

* **Fedora:**

  ```bash
  sudo dnf install python3-tkinter
  ```

---

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/OTAKUWeBer/ChessPilot.git
   cd ChessPilot
   ```

2. **Install Python Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Add Required Files:**

   * Place the downloaded ONNX model (`chess_detectionv0.0.4.onnx`) and Stockfish ZIP file (e.g., `stockfish-windows-x.zip`) directly into this folder.

---

## Platform Notes

### Linux Users

Install Stockfish via your package manager:

```bash
# Ubuntu / Debian
sudo apt install stockfish

# Arch Linux
paru -S stockfish

# Fedora
sudo dnf install stockfish
```

#### Wayland Users (Hyprland, Sway)

You will need additional tools for screenshots and screen size detection:

```bash
sudo pacman -S grim wayland-utils
```

---

## Usage

1. **Run the Script:**

   ```bash
   python main.py
   ```

2. **Choose Your Color:**

   * Select **White** or **Black**.
   * Press **ESC** to reselect.

3. **Enable Castling (If Applicable):**

   * Tick **Kingside** or **Queenside** before each move if you still retain castling rights.

4. **Set Move Depth (Optional):**

   * Adjust the slider to increase/decrease Stockfish analysis depth.
   * Default is **15**—good balance of speed and accuracy.

5. **Play Modes:**

   * **Manual Mode**: Click **"Play Next Move"** for each move.
   * **Auto Mode**: Enable **Auto Play** to let the script make your next move automatically.

6. **Retry System:**

   * The tool will retry move execution up to **3 times** if it fails initially.

7. **Tips for Accuracy:**

   * Use **100% zoom** in your browser or chess interface.
   * Keep the Tkinter window out of the way of the board.
   * Keep your board square and aligned.

---

## Disclaimer

🛑 **Use at Your Own Risk**: Automating chess play may violate terms of service on online platforms. You are responsible for how you use this tool.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests if you have suggestions or improvements.

---

## Acknowledgments

* Thanks to [Zai-Kun](https://github.com/Zai-Kun) for the ONNX chessboard detection model and Wayland support.