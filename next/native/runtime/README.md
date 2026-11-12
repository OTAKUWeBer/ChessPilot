# Native runtime boundary

The `chesspilot-runtime` cdylib exports four C ABI functions. Dart's `native_client.dart` is the current caller; both sides are built from the same revision.

```c
uint8_t *chesspilot_alloc(size_t length);
char *chesspilot_request(const uint8_t *input, size_t length);
void chesspilot_free_input(uint8_t *input, size_t length);
void chesspilot_free_response(char *response);
```

Allocate input in Rust, copy initialized UTF-8 JSON bytes, call synchronously, and release both buffers exactly once with their matching Rust functions. Requests are length-delimited (maximum 1 MiB); responses are NUL-terminated JSON. Do not free Rust allocations with the Dart or C allocator. Invalid pointers are outside the ABI's safety contract; invalid JSON, UTF-8, session IDs and request fields return structured errors. Panics in request dispatch are contained at the boundary.

Responses are `{"ok":true,"result":...}` or `{"ok":false,"error":"..."}`. `open` returns a session ID and initial state. Other commands include `session`:

* `configure`: optional `color` (`w`, `b`, null), `depth` (10-30), `delay` (0-1), `mode` (`drag`, `click`), and castling booleans. All fields validate before committing.
* `initialize_engine`: optional explicit `engine_path` and `config_path`. Returns quickly; a native worker owns engine initialization. Default engine lookup uses installed/development resource locations and PATH. Android library-based engine integration is not implemented yet.
* `analyze`: a full `fen` for a position already established by the application pipeline; returns quickly. The eventual capture/controller will call this boundary. The UI does not add a temporary manual-FEN product flow.
* `status`: current settings, color, busy/error/status, capability flags and latest analysis.
* `stop`: invalidates queued/ongoing analysis generation immediately and requests engine stop. Busy remains true until the worker acknowledges completion.
* `close`: removes the session from the registry, cancels and joins work, and disposes the engine. It can block, so Dart performs it in a background isolate. Desktop-window exit must eventually await this operation through the platform close lifecycle.

Capture/automation capability flags remain false until actual backends are connected. Progress/analysis includes a session generation; stale worker results cannot update a newly selected color. Multiple clients can own separate sessions, but one session admits only one engine job at a time. Native state is authoritative; Dart snapshots contain no separate chess rules or engine state.

The UI currently polls status while a native operation is busy; capture frames and model tensors never cross this JSON UI boundary. Logging installation/download, frame transport, OS input, desktop shutdown and Android service ownership remain migration work.

## Perception module

`vision::BoardReader<OnnxPredictor>` owns a persistent native ONNX session and consumes checked packed RGB frames. It ports Python's 640×640 Pillow Lanczos letterbox, RGB/CHW float32 normalization, output decoding, board-crop refinement and overlapping tile search. All boxes return in capture-frame coordinates. Raw detection for promotion dialogs can disable refinement.

ONNX Runtime is loaded explicitly from a shared library, using the 1.20 C API; no Python interpreter is involved. One process pins one runtime-library path. Model shape/type mismatches and unreadable positions return errors or no result. Cancellation is checked before and after each inference; an in-flight native inference completes before cancellation takes effect. Search is capped at 64 inferences per observation.

The module is tested independently of capture. Session/UI capture capability remains false until a real capture backend and its lifecycle are connected. See `tests/fixtures/vision/README.md` for Python reference provenance and real-model parity checks. The resampling contract follows Pillow; its license is retained in `third_party/Pillow-LICENSE.txt`.
