# Contributing to ChessPilot

Thank you for your interest in contributing to ChessPilot! We welcome contributions ranging from bug fixes and documentation improvements to platform enhancements.

---

## 🛠️ Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/OTAKUWeBer/ChessPilot.git
   cd ChessPilot
   ```

2. **Create and activate a virtual environment:**
   - **Windows:**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch development build:**
   ```bash
   python src/main.py
   ```

---

## 🧪 Running Tests

Before submitting any code changes, ensure all tests pass:

```bash
python -m unittest discover tests -v
```

To run a specific test suite:
```bash
python -m unittest tests/test_fen_and_notation.py -v
python -m unittest tests/test_move_validation.py -v
python -m unittest tests/test_engine_service.py -v
python -m unittest tests/test_archive_extraction.py -v
python -m unittest tests/test_downloader_and_cpu.py -v
```

---

## 📐 Architecture & Coding Guidelines

ChessPilot follows a clean desktop modular architecture:

```
src/
├── board_detection/   # ONNX inference, box normalization, FEN spatial extraction
├── core/              # Pure chess coordinate conversions, FEN logic, and AppConfig
├── game/              # Move execution, auto-play background loop, promotion, validation
├── gui/               # PyQt6 widgets, buttons, shortcuts, and download dialog
├── services/          # Stockfish UCI engine process supervisor
├── utils/             # Hardware CPU detection, logging, resource paths, system I/O
└── wayland_capture/   # Native Linux Wayland socket protocol input injection
```

### Core Principles:
- **100% Offline by Default**: The game loop and engine analysis must never depend on an active internet connection.
- **Cross-Platform Safety**: Always test or preserve both Windows (`win32api` / PyAutoGUI) and Linux (Wayland socket protocol) code paths.
- **Strict Exception Handling**: Never use bare `except Exception: pass` or `except: pass`. Catch specific exception types and log them using `logger.debug()`.
- **Thread Safety**: Any UI updates from worker threads must be dispatched via `QTimer.singleShot` or PyQt signals.

---

## 📬 Submitting a Pull Request

1. **Fork** the repository and create your feature branch:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. **Commit** your changes with clear, descriptive commit messages.
3. **Push** to your fork:
   ```bash
   git push origin feature/my-new-feature
   ```
4. Open a **Pull Request** targeting the `main` branch. Fill out the PR template checklist completely.
