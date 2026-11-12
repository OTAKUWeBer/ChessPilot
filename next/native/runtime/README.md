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
