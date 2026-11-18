# Architecture and development

The repository root contains `app/` (Flutter and native runners), `native/` (Rust workspace), `tool/` (build/release helpers), `assets/` (model and artwork) and `packaging/` (Windows installer).

## Runtime flow

Rust owns a session and one serialized worker: in-memory capture → persistent ONNX detection → Stockfish analysis → fresh pre-input board check → native input → visual confirmation. Predicted positions remain separate from confirmed history. Cancellation/generation IDs prevent late work from committing after Stop or a settings change. Uncertain gestures are not automatically repeated.

The detector uses RGB Lanczos/letterbox preprocessing, validated output mappings and bounded crop/tile refinement. The exact model is checked by SHA-256. Frozen tensor, geometry, promotion and protocol fixtures cover regression behavior; their provenance is documented alongside the data.

Stockfish is a persistent UCI child with bounded handshake/search/stop waits, drained output/error streams and restart on the next request after failure. Exit sends `quit`, then kills/reaps an unresponsive child. Stop may retain a healthy engine for reuse. Desktop downloads are CPU-compatible, hash/architecture/UCI checked and cached; Android packages compatible PIE executables and network data.

## Platform boundaries

- Windows: GDI capture and SendInput, physical-pixel coordinates with monitor origin and scoped DPI context.
- Linux: native X11/XTEST or wlroots screencopy/virtual-pointer with `grim`. Portal control is unfinished. Keep the session's normal display environment.
- Android: Kotlin owns MediaProjection, accessibility gestures, foreground lifecycle and the movable overlay. JNI connects the process-owned Rust session; Flutter adopts that session across Activity recreation. Measured overlay bounds are masked and guarded against input intersections.

Flutter snapshots contain presentation state; Rust owns settings, readiness, analysis, confirmed history and game results. Dart/native buffers have paired allocation/free functions. See [the native runtime contract](../native/runtime/README.md) for commands and ABI details.

## Android controls

The full Flutter dashboard holds setup/settings. The accessibility service owns a movable 48 dp logo bubble and a 216 dp expanded panel, about 111 dp tall at normal text scale. Metadata/status are separate from the four action buttons; large text stacks the controls. Actions have at least 48 dp touch targets. Dragging or opening the dashboard pauses automation.

Controls respect system-bar/cutout bounds and remember edge/relative placement. The runtime masks measured overlay bounds, rejects covered boards and gestures crossing the controls, and discards stale geometry after movement/rotation. Expanding/collapsing does not initiate a move. Notification controls provide another route to Stop/Exit. Physical cases and remaining device checks are recorded in the test guide.

## Development guides

- [Installation and first launch](INSTALLING.md)
- [Build prerequisites and commands](BUILDING.md)
- [Tests and platform evidence](TESTING.md)
- [Engine configuration](ENGINE_CONFIG.md)
- [Version and release maintenance](RELEASING.md)
