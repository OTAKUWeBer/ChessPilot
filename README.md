# Chess Position Evaluator (Roblox & Chess.com Friendly)

<p align="center">
  <img src="assets/chess-banner.jpg" alt="Chess Banner" width="600" />
</p>

## What’s Changed & Why

* **Maia Integration**

  * Stockfish has been completely replaced with the human-like Maia engine (`lc0.exe` + `maia-1600.pb.gz`).
  * Users reported account bans on Chess.com when using Stockfish due to its inhumanly perfect play. Maia’s move suggestions mimic a \~1600 Elo human, making them less likely to be flagged by cheat detectors.

* **Visits Slider (formerly "Depth Slider")**

  * Renamed to **"Maia Visits"** in the GUI to reflect the number of Monte‑Carlo Tree Search visits.
  * Default set to **100 visits**, adjustable from 10–500 visits for a balance between speed and human‑like accuracy.

* **Win32‑Only Automation**

  * Removed all Linux and `pyautogui` code. The bot now uses native Win32 API calls (`win32api`/`win32con`) for clicking, ensuring compatibility with Roblox’s 2D Chess Club game and other Windows‑only clients.

* **Roblox 2D Chess Support**

  * Switched from click‑drag to click‑click piece movement to accommodate Roblox’s input model.
  * Tested with the Roblox game **♟️Chess Club♟️ \[UPDATE]** (ID: 139394516128799) in 2D mode.

## Installation & Setup

1. **Clone the Repository**

   ```bash
   git clone https://github.com/OTAKUWeBer/ChessPilot.git
   cd ChessPilot
   ```

2. **Install Python Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Board Detection Model**

   * Download `chess_detection.onnx` from Zai‑Kun’s detection repo:
     [https://github.com/Zai-Kun/2d-chess-pieces-detection/releases/latest](https://github.com/Zai-Kun/2d-chess-pieces-detection/releases/latest)
   * Rename to `chess_detection.onnx` and place alongside `main.py`.

4. **LCZero (`lc0.exe`)**

   * Download the latest Windows binary from:
     [https://github.com/LeelaChessZero/lc0/releases](https://github.com/LeelaChessZero/lc0/releases)
   * Rename to `lc0.exe` and place it in the project root.

5. **Maia Weights**

   * Download `maia-1600.pb.gz` from CSSLab’s Maia repository:
     [https://github.com/CSSLab/maia-chess/releases/latest](https://github.com/CSSLab/maia-chess/releases/latest)
   * Create a folder `models/` next to `main.py` and place the weights inside.

6. **Run the App**

   ```bash
   python main.py
   ```

## Usage

1. **Select Playing Color** (White/Black) in the GUI.
2. **Adjust "Maia Visits"** slider (10–500).
3. **Play Next Move**:

   * Click **"Play Next Move"** for manual mode.
   * Enable **"Auto Play Moves"** to automate moves after your opponent.
4. **Castling Rights**: Tick **Kingside/Queenside Castle** if needed before each move.
5. **ESC Key**: Press to reset color selection at any time.

## Conversational Context & Use Cases

> “I got banned on Chess.com using Stockfish—it’s just too perfect. Switched to Maia and my 1400 Elo account stayed safe. Also, Roblox’s 2D Chess Club doesn’t support drag, so we moved to click‑click.”
>
> — ciggyblacc & weberz (12:51–13:04)

* **Chess.com**: Maia’s human‑like mistakes reduce cheating flags.
* **Roblox Chess Club**: Win32 click‑click ensures reliable piece movement.

## Disclaimer

🛑 **Use at Your Own Risk**: Even human‑like engines may violate Terms of Service on some platforms.

## License & Contributing

* Licensed under the **MIT License**.
* Contributions welcome—especially for additional Maia skill levels, improved board detection, or integrating with other Windows games and sites.