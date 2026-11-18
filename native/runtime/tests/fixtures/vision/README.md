# Vision regression fixtures

`demo.rgb` is a 568×318 packed RGB test frame retained from the original project's demo. No personal desktop capture is included. `reference.json` records reference preprocessing and detection results, model checksum and generation metadata. Source/provenance fields in the data are intentionally retained.

The model is `assets/models/chess_detection.onnx`, with its tracked SHA-256 manifest. Desktop and Android builds package the same bytes; Android verifies its private installed copy. Pillow-derived RGB Lanczos/letterbox preprocessing retains the corresponding license notice.

Preprocessing tests construct deterministic RGB patterns and compare the complete float32 tensors. Scene cases cover normal inference, small-board recovery and an unreadable board; coordinate/FEN results and all class mappings are checked. Normal detection confidence is 0.5; refinement is bounded.

Set `CHESSPILOT_MODEL` and `CHESSPILOT_ORT` for the real inference check:

```sh
cargo test --manifest-path native/Cargo.toml --release --locked --test vision actual_onnx_inference_and_zoom_search_match_reference -- --ignored
```

An optional private-image comparison accepts an externally generated `CHESSPILOT_PARITY_REPORT`, with the same model/runtime variables. Its test is `actual_reported_image_matches_reference`. Reference generation is separate from this repository and is not a build requirement. Do not commit private screenshots or generated reports.
