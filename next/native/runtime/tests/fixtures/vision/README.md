# Python reference fixtures

`demo.rgb` is packed RGB frame 0 of the repository's `assets/demo.gif` (568×318). No user desktop content was captured to create it.

`python.json` records outputs from the unchanged Python `board_detection/get_positions.py` using Pillow 12.1.0, NumPy 2.4.1, ONNX Runtime 1.20.0 and the current `src/chess_detection.onnx` (SHA-256 `c5dd2f875f6f7efcc12a40ccd15bbb57158a558ac6206949c63bb804b2086c91`).

For each preprocessing pattern, construct RGB bytes `(i*37+11)%256` at the given dimensions, call Python `preprocess_image`, and FNV-1a hash its contiguous float32 tensor bytes. Hashes are regression checks, not security/integrity signatures. Rust checks the actual tensor bytes, not merely whether a resize method is called Lanczos.

For each scene, resize the demo to the supplied width (height uses rounded aspect ratio), paste it at the offset on an RGB canvas filled with `(32,32,32)`, and run Python `get_positions` and `get_fen_from_position('w', boxes)`. The scenes cover normal inference, recovery where the full-screen model finds nothing, and a genuinely unreadable small board. The reference includes all boxes and their global coordinates; confidences allow 1e-5 floating-point tolerance while coordinates, classes and FEN must match exactly.

The real model/runtime integration test is explicit: set `CHESSPILOT_MODEL` and `CHESSPILOT_ORT`, then run the vision test with `--include-ignored`. Without those native assets, unit tests still run, but do not establish real inference parity.
