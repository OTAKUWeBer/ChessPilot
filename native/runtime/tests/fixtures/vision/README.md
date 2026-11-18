# Python reference fixtures

Commands and output paths in this guide are relative to the Rust project root, the folder containing `app/`, `native/` and `tool/`.

`demo.rgb` is packed RGB frame 0 of the Python main branch's historical `assets/demo.gif` (not shipped here) (568×318). No user desktop content was captured to create it.

`python.json` records outputs from the unchanged Python `board_detection/get_positions.py` using Pillow 12.1.0, NumPy 2.4.1, ONNX Runtime 1.20.0 and the current `assets/models/chess_detection.onnx` (SHA-256 `c5dd2f875f6f7efcc12a40ccd15bbb57158a558ac6206949c63bb804b2086c91`).

For each preprocessing pattern, construct RGB bytes `(i*37+11)%256` at the given dimensions, call Python `preprocess_image`, and FNV-1a hash its contiguous float32 tensor bytes. Hashes are regression checks, not security/integrity signatures. Rust checks the actual tensor bytes, not merely whether a resize method is called Lanczos.

For each scene, resize the demo to the supplied width (height uses rounded aspect ratio), paste it at the offset on an RGB canvas filled with `(32,32,32)`, and run Python `get_positions` and `get_fen_from_position('w', boxes)`. The scenes cover normal inference, recovery where the full-screen model finds nothing, and a genuinely unreadable small board. The reference includes all boxes and their global coordinates; confidences allow 1e-5 floating-point tolerance while coordinates, classes and FEN must match exactly.

The real model/runtime integration test is explicit: set `CHESSPILOT_MODEL` and `CHESSPILOT_ORT`, then run `cargo test --manifest-path native/Cargo.toml --test vision actual_onnx_inference_and_zoom_search_match_python -- --ignored`. Without those native assets, unit tests still run, but do not establish real inference parity.

Both desktop and Android builds copy the existing Python model from `assets/models/chess_detection.onnx`; they do not download a replacement model. The Windows release and both Android debug APK outputs were checked against that source file by SHA-256. Android also packages the generated checksum and checks its private model at startup, so an app update cannot silently keep an older model.

Private-image parity checks accept an externally generated reference report through `CHESSPILOT_PARITY_REPORT`, with `CHESSPILOT_MODEL` and `CHESSPILOT_ORT` selecting the model/runtime. Run `cargo test --manifest-path native/Cargo.toml --test vision actual_reported_image_matches_python -- --ignored`. Reference generation belongs in a separate Python checkout and is not a build requirement.

The generated RGB frames and report stay under ignored `target/`; do not commit private screenshots. The check compares the model hash, all 12 piece mappings, board/promotion IDs, FEN for both colors, inference counts and every returned box across 16 cases: original, smaller on 1080p, on 4K and unreadably tiny, each at confidence 0.5/0.6 with refined search disabled/enabled. The application's default confidence remains Python's 0.5.

On the reported zoom screenshot, original detection succeeded directly, the 1080p and 4K cases needed refined search (4 and 6 inferences), and the unreadable case failed in both implementations. The application reports detection failure after refined search and cannot proceed to engine analysis or piece input for that observation.
