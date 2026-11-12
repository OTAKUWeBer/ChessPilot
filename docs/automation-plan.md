# ChessPilot automation: Rust, Windows, Linux and Android

Prepared 12 November 2026. Design companion to the [whole-app migration plan](android-pc-migration-plan.md) and [complete source/function inventory](migration-code-inventory.md), based on v2.3.1 commit `cbe8566d39953a510e20748e6d53165a78822f91`.

## The decision

**Keep one Rust automation controller, with a small native input/capture adapter for each platform.** Flutter draws controls; it does not simulate input into another app. Stockfish supplies a move; Rust validates it, converts squares to coordinates, dispatches the action, and checks the actual board afterward. No Python interpreter or PyAutoGUI is required in the new runtime.

The current Windows path already uses `win32api.SetCursorPos` and `mouse_event` in `game/move_execution.py`. PyAutoGUI provides the non-Windows/non-Wayland fallback. Wayland uses the handwritten `WaylandInput` client. The migration replaces these implementations while preserving click mode, drag mode, manual play, auto mode, castling, promotion, stop, and verification.

| Platform | Input decision | Capture decision | Permission/capability dependency |
| --- | --- | --- | --- |
| Windows | Rust `windows` bindings to Win32 `SendInput`; physical desktop coordinates | DXGI Desktop Duplication for the selected monitor | Interactive desktop and compatible target integrity; detect blocked input |
| Linux X11 | Rust `x11rb`, XTEST motion/button requests | Selected X11 output/root region through the same connection | Authorized X connection with required extensions |
| Linux Wayland | Portal RemoteDesktop session; prefer EIS input where available, otherwise portal pointer methods; explicit wlroots virtual-pointer fallback | Portal ScreenCast/PipeWire; tested `grim` fallback only on supported compositors | User-granted session, advertised pointer/capture capabilities, valid coordinate mapping |
| Android | Rust request -> JNI -> Kotlin AccessibilityService -> tap/drag gesture | MediaProjection foreground service -> native frame buffers | User-enabled accessibility service, capture consent, and appropriate foreground-service setup; floating controls separately |

Implementation progress is tracked in [next/README.md](../next/README.md). Windows now has controlled-board integration coverage. X11 and the existing wlroots route are connected and Linux compile/lint checks pass; live Linux validation is left to the user's machine. Android services, JNI/frame/gesture bridge and compact movable overlay are connected and build as an ARM64 debug APK; device checks are deferred until the user connects ADB. Portal support remains planned. Kotlin is the Android lifecycle/API boundary. A single Rust input library cannot remove those OS restrictions.

## 1. Windows backend

Use the same native Windows family of APIs the application already relies on. The Rust `windows` crate also supplies the desktop capture bindings, so using Win32 directly avoids adding a second generic input library solely for mouse operations. [Microsoft Rust Windows bindings](https://github.com/microsoft/windows-rs).

Implement these sequences:

* **Click mode:** move to source, left down/up, settle as required by the target board, move to destination, left down/up.
* **Drag mode:** move to source, left down, retain the press through intermediate motion events, reach destination, left up. Preserve the intermediate-event behavior that fixed Chromium drag recognition; timing remains calibrated.
* **Promotion:** click the verified menu target, then confirm the promoted piece on the board.
* **Cursor relocation:** a movement-only operation after manual play; never encode it as a click. Keep it optional on desktop and omit it on Android.

Check inserted-event counts and report failures. Input is subject to Windows integrity restrictions; an unelevated process cannot reliably inject into an elevated target. Do not automatically elevate ChessPilot. A successful API call means events were inserted, not that the board accepted a chess move. [SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput).

For absolute injection, use the full virtual desktop and normalized coordinates required by `MOUSEINPUT`; preserve negative monitor origins and per-monitor DPI awareness. Test the physical-point-to-normalized-point transform, endpoints, and mixed-DPI configurations. Do not feed Flutter logical pixels directly to input. [MOUSEINPUT coordinates](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-mouseinput).

DXGI capture provides desktop frames through a surface. The adapter owns acquisition/release, pixel conversion and rotation, and recreates capture after display/session changes. Preserve the selected output's bounds with every frame. Do not capture a monitor-local image and forget its global origin. [Desktop Duplication API](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/desktop-dup-api).

Release gate: click and drag on a controlled board, current Chromium-based browser behavior, another tested browser, negative-origin second monitor, 100/125/150/200% scaling, display change, lock/unlock, partial input failure, and stop while a button is held. Native failure cleanup must attempt to release a button owned by this session.

## 2. Linux X11 backend

Use `x11rb` for X11 connection, monitor/capture metadata, and XTEST event injection. Probe XTEST and the needed capture/output extensions before enabling automatic play. Generate real pointer/button events rather than relying on widget-specific messages. Maintain one connection for the session, flush action batches appropriately, and expose connection/extension failures. [x11rb source](https://github.com/psychon/x11rb).

The click/drag intent is shared with Windows, but event formatting and coordinate conversion remain in the X11 adapter. Resolve output bounds and image byte order/stride explicitly. Test left-of-primary monitors and reconnect behavior.

Do not treat an available `DISPLAY` variable as proof of a native X11 session: Wayland sessions can also expose XWayland. Select the backend from the actual session/capture route and capabilities. Do not assume XTEST over XWayland controls native Wayland windows.

Release gate: genuine X11 desktop, required extension unavailable, authorized-connection loss, both input modes, promotion, and physical coordinate alignment. Add one Linux engine/model integration job; a Windows executable existence check must not skip it.

## 3. Linux Wayland backend

### Prefer a user-granted portal session

Use a session shared by RemoteDesktop and ScreenCast. Request pointer capability and the intended capture source, start it through the system approval flow, and inspect the actual granted capabilities. Obtain the PipeWire stream for frames. Prefer `ConnectToEIS` when available; use the portal pointer methods only where supported. A closed/revoked session invalidates both capture and input state. [RemoteDesktop portal](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html).

Once EIS is connected, send all session input through it; do not mix it with portal `Notify*` calls. Probe interface versions before connecting, and end the session if EIS disconnects. Select the legacy pointer path before EIS connection when EIS is unavailable.

Use Rust `ashpd` for portal requests and the combined-session lifecycle. It documents using ScreenCast source selection on a RemoteDesktop-created session. For EIS, choose a tested Rust client or binding to libei during the spike; `reis` is a candidate whose own documentation describes incomplete APIs, so it is not an unconditional dependency choice. Bind to mapped regions/devices before injecting absolute motion. [ashpd combined sessions](https://docs.rs/ashpd/latest/ashpd/desktop/remote_desktop/index.html), [reis limitations](https://docs.rs/reis/latest/reis/).

Separate the capture buffer's pixels from portal stream coordinates and EIS device-region coordinates. Derive the mapping from the negotiated stream/region metadata. If a capture source cannot be mapped to an absolute pointer region, disable automation for that source rather than guessing.

### Retain the working wlroots route where needed

The current code requests `zwlr_virtual_pointer_manager_v1`. Preserve that capability for a compositor that advertises it. The initial Rust port retains the small socket client to keep the existing behavior, with strict v1 messages, bounded stream handling, fresh callback IDs and persistent pointer cleanup. Frozen Python gesture traces plus a fragmented fake compositor check this restricted protocol surface. Capture uses `grim` at logical layout scale; it is not a Python dependency. If this backend expands to output/seat discovery or other protocols, replace the handwritten codec with [wayland-rs](https://github.com/Smithay/wayland-rs) and [generated wlroots bindings](https://github.com/Smithay/wayland-rs/tree/master/wayland-protocols-wlr). Real compositor validation and the portal path remain release gates; see [Linux checks](../next/linux-testing.md).

Do not fall back to another route after the user explicitly denies access. If neither authorized path is available, report the missing capability and retain image/FEN analysis. This is an unsupported automation configuration, not successful platform parity.

### Do not assume one crate covers every Wayland desktop

Enigo is a possible convenience library for some targets; its upstream documentation flags Wayland/libei limitations. Do not make generic Enigo support the acceptance test. Our requirements include shared capture/input session ownership, absolute stream mapping, revocation and compositor coverage, so the plan uses explicit backends. If a pinned Enigo version later meets those requirements with less code, it can replace implementation detail behind the same small boundary. [Enigo upstream](https://github.com/enigo-rs/enigo).

Required matrix: GNOME Wayland, KDE Plasma Wayland, and at least one wlroots compositor used by current users. Record compositor/portal versions and the backend actually selected. Exercise multi-output layout, scaling, rotation, denial/revocation and missing protocol. Release support only for configurations that pass; keep Python available while parity is incomplete.

## 4. Android backend

Current implementation and deferred acceptance are recorded in [Android setup](../next/android-testing.md). The [phone overlay plan](phone-overlay-plan.md) specifies the 48 dp draggable bubble and compact panel; the PC window size does not apply to that surface.

### Rust owns decisions; native services perform Android operations

The phone cannot use desktop cursor calls. Keep the app logic in Rust, with a small Kotlin boundary that Android can instantiate as actual services:

```text
Flutter dashboard / small floating controls
                 |
           Rust session owner
          /                  \
native ONNX + Stockfish    Input request with IDs/coordinates
          ^                  |
          |                 JNI
MediaProjection buffers      |
          ^           Kotlin AccessibilityService
          |                  |
Capture foreground service   +--> GestureDescription --> Android touch
```

The capture foreground service starts/owns the native session after user initiation. The accessibility service has its own Android-managed lifecycle. Both expose connection/permission changes to that session owner. Flutter's activity can be backgrounded without taking the active controller with it; killing/recreating the process does not silently resume play. There is exactly one runtime session handle per process, not one per screen or service callback.

### Capture and coordinate alignment

Use MediaProjection rather than repeatedly launching an external screenshot command. The capture service supplies image format, row/pixel stride, timestamp, rotation, display/source bounds and a geometry revision with its buffers. Register termination/resize handling. The service must meet the media-projection foreground-service declarations and runtime prerequisites. [Android foreground-service types](https://developer.android.com/develop/background-work/services/fgs/service-types#media-projection).

Start the automation prototype with a consented full-display source, because mapping a captured display to touch coordinates is simpler than mapping an independently scaled single-app image. Android 14+ offers both capture choices; a cropped/app-only stream is not automatically global touch space. Enable app-only automation only after its origin, letterboxing, scale and visible bounds can be established. Recalibrate after rotation, split-screen, keyboard/system-inset changes, or capture-source resize. [MediaProjection capture choices](https://developer.android.com/media/grow/media-projection).

### Taps and drags

Declare the accessibility service with the gesture capability, then let the user enable it in system settings. Rust submits a bounded input request through JNI; Kotlin constructs a `GestureDescription` and calls `dispatchGesture`. A return of `false` rejects the request. Only one gesture is active at a time: dispatching another can cancel existing gestures, including the user's. [AccessibilityService gesture API](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService).

Use one short stationary stroke for a tap; a drag is one continuous stroke from source to destination. Click mode uses two taps sequenced by completion, with only the measured settling delay needed by the target. Calibrate durations on actual devices rather than copying the desktop's tiny delays. [Gesture stroke description](https://developer.android.com/reference/android/accessibilityservice/GestureDescription.StrokeDescription).

Propagate `onCompleted`/`onCancelled` back to Rust with session/action IDs. Completion is delivery evidence, so board verification still determines chess success. A callback deadline produces `uncertain`, not another blind gesture. An API timeout must not release a native request handle that a later callback can still access. [Gesture result callbacks](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService.GestureResultCallback).

Use screen coordinates rather than requiring chess-square accessibility nodes: image/canvas boards may not expose useful per-piece nodes. Keep all move rules and menu selection in the shared controller. The service does not run a second chess engine.

### Floating controls and stop

Provide a compact Play/Auto/Stop surface that does not cover the board. Because a user-enabled accessibility service is already required for input, first test an accessibility overlay; request separate general overlay access only if the chosen overlay implementation actually needs it. The window type, service ownership, focus and touch behavior must be intentional. No invisible full-screen touch-catching window is needed. [Android window types](https://developer.android.com/reference/android/view/WindowManager.LayoutParams).

Exclude, hide or mask the controls during capture, and revalidate after any temporary overlay change. Input must not land on ChessPilot's own controls. Keep a notification Stop action, service stop handling, and a clear route back to the main dashboard. Stop invalidates queued actions immediately. An already-dispatched gesture may finish; ignore its stale result for scheduling and never follow it with another action. Do not promise that a foreground service survives process death or every vendor power policy.

### Distribution constraint

The engineering scope includes the current auto-play loop. Separately, Google Play restricts autonomous decisions executed through AccessibilityService, and Stockfish chooses moves dynamically. Confirm an acceptable distribution route before promising full auto mode in Play. A direct-install APK still requires explicit user enablement and all relevant platform setup; it does not bypass Android controls. [Google Play Accessibility API policy](https://support.google.com/googleplay/android-developer/answer/10964491?hl=en).

Android release gate: two physical phones of different performance, portrait/landscape, full-display capture mapping, backgrounded activity, service recreation, capture/accessibility loss, overlay interaction, gesture cancellation, blocked/unreadable capture, low-memory pressure and sustained play on a controlled board.

## 5. Shared Rust action pipeline

The application needs chess-oriented actions, not an automation scripting language. Keep a small input boundary with `tap`, `drag`, desktop-only `move_pointer`, capability query and cleanup. Keep the capture boundary responsible for frames plus coordinate metadata. Dispatchers return typed results; they do not touch UI state.

Each action contains `session_id`, `observation_id`, `action_id`, geometry revision, source/destination points, input mode, and a deadline. Promotion selection is another tap from a newly observed menu, not an opaque extension of an old coordinate command. No platform adapter chooses a chess move.

One move proceeds as follows:

1. Confirm capture and input capabilities are active; capture a stable board and establish legal position/turn metadata.
2. Analyze that observation with Stockfish; retain the expected legal position separately from confirmed state.
3. Before input, validate that position, geometry, selected source and session still match. Reacquire if the window, monitor, board orientation, zoom or phone rotation changed.
4. Map squares to input points; keep the entire gesture within verified source/destination geometry. Dispatch exactly one action.
5. Wait for transport/API delivery evidence. On OS failure, record `not_dispatched` or `uncertain` as appropriate; no success message yet.
6. Detect promotion/castling behavior from new frames. Use actual target behavior to decide whether any extra selection/rook action is needed.
7. Verify the expected legal outcome. Permit a known legal immediate opponent reply only when history supports it. Commit confirmed state, emit status, and wait for the opponent.
8. If confirmation is ambiguous, pause, capture again and offer a deliberate retry/resync. Never re-send merely because an acknowledgement or screenshot was late.

Auto mode repeats this state machine on legal board transitions; it does not create an additional worker per observed frame. Manual mode submits one move through the same owner. Stop/color/source changes invalidate old analyses and input requests. UI events carry IDs so late callbacks cannot revive an old session.

### Geometry invariant

Preserve these spaces explicitly:

`model tensor -> captured frame -> board rectangle -> platform input coordinates`.

Undo letterbox and crop/tile offsets exactly once. For a canonical square `(file, rank)` with zero-based `a=0` and `1=0`, white-bottom uses `(column=file, row=7-rank)` and black-bottom uses `(column=7-file, row=rank)`. Then the frame-space center is `x = left + (column+0.5)*width/8`, `y = top + (row+0.5)*height/8`. Apply the capture-to-input transform afterward. Use independent width/height and retain fractional precision until the backend needs integers.

That final transform is different on each platform: monitor origin/DPI on PC, stream-to-device mapping on Wayland, display/source rotation/scale/insets on Android. If it is unknown or stale, no gesture is valid. Random offsets, if retained, stay bounded inside the actual square; start with deterministic centers for calibration and tests. Fixed `±16` pixels is unsafe on tiny zoomed boards. Randomness is not a reliability requirement.

### Error and cleanup behavior

Distinguish `permission_needed`, `unsupported_backend`, `capture_lost`, `geometry_changed`, `not_dispatched`, `uncertain_delivery`, `verification_failed`, and `stopped`. Show the corresponding recovery action instead of blaming Stockfish or retrying input indefinitely.

Allow at most one in-flight gesture and bounded observation/analysis queues. A desktop backend tracks whether it owns a held mouse button and attempts release on cancellation/error. Android retains callback ownership until completion/cancellation or safe service teardown. Revoke/restart always establishes a new session. Avoid broad exception-swallowing behavior and global counters shared by unrelated sessions.

## 6. Current code to new implementation

The inventory lists every function. This table resolves the automation-specific destinations into concrete responsibilities, including existing callers.

| Current code | Replacement |
| --- | --- |
| `MoveExecutionMethods.drag_piece`, `click_piece` | Windows/X11/Wayland/Android input adapters; common calibrated gesture intent, native events per platform |
| `_safe_disable_auto_mode`, duplicated `_disable_auto_mode` helpers | One session stop/pause transition plus a UI event |
| `MoveExecutor.move_piece`, `execute_move`, `_execute_physical_move` | Serialized action dispatch with IDs, current geometry, delivery result and cleanup |
| `convert_move_to_indices`, `_get_move_positions`, `core/notation.py`, both board-position storage implementations | One validated square-to-point transform; no UI-dependent parsing or duplicate board geometry |
| `execute_normal_move`, `_attempt_single_move`, `_verify_move_execution`, result handlers | Shared execute/verify states; uncertain input pauses instead of unverified success |
| `move_processor._execute_move`, castling helpers and verification | Legal expected castling transition; king action, fresh rook observation and explicit fallback only when needed |
| All promotion discovery, wait, selection and retry helpers | Raw-menu observations, bounded menu acquisition, native tap, all-four-piece verification |
| `MoveValidator` pure comparisons and live `verify_move` | Legal expected-transition checks in core; frame acquisition and deadlines in runtime |
| `auto_play.py` seeding, polling, turn handlers, delays, thread/controller wrappers | One cancellable runtime session driven by stable observations and known legal history |
| `WaylandInput` socket setup, encoding, event parsing, pointer creation, click/swipe methods | Ported restricted wlroots v1 client with persistent resources/layout coordinates; portal session/EIS adapter still planned |
| `wayland_capture/screen.py:get_resolution` | Capture/output metadata with typed dimensions and transform revision |
| `capture_screenshot_in_memory`, `get_binary_path('grim')` | Native capture adapters; negotiated portal PipeWire source or supported transitional helper |
| `move_cursor_platform_specific`, `calculate_button_center`, `move_cursor_to_button`, `get_button_info` | Optional desktop pointer relocation from UI-reported screen bounds; not part of executing a chess move |
| `main.py` thread launches and auto/close callbacks, `gui/shortcuts.py` stop/color changes | Typed commands and lifecycle acknowledgements; no stale action after leaving play mode |
| `board_reader`, detector normal/refined search | Shared observed frames, cached ROI, normal/refined fallback, geometry IDs and bounded model work |
| `AppConfig` retry, interval and verification flags | Typed settings with calibrated timing; remove unverified-success behavior while preserving failure recovery |

## 7. Implementation order and pass conditions

This expands phases 1-7 of the whole-app plan; it is not a second parallel rewrite or an added delivery estimate.

| Step | Deliverable | Pass condition |
| --- | --- | --- |
| A. Input/capture spike | Minimal Windows and physical-Android tools using the proposed native boundaries, plus Wayland capability probe | Record a frame, target known squares, deliver one move and stop; verify positions on the screen. A phone image-import demo is insufficient. |
| B. Shared geometry/controller | Pure Rust position/orientation/transform/state tests, fake capture/input backends, cancellable IDs | Both orientations, crop/tile/letterbox transforms, stale geometry, duplicate Play, timeout and uncertain-delivery tests pass |
| C. Windows product path | Native capture/input plus Flutter controls, engine and verification | Full current Windows automation matrix passes; compare end-to-end timing against Python |
| D. Android product path | Capture foreground service, accessibility gestures, overlay, Rust runtime and callbacks | Manual and auto play work while Flutter UI is backgrounded; revoke/lock/rotate/cancel behavior passes on both phones |
| E. X11 and Wayland parity | X11 connection, portal session, tested wlroots fallback and explicit capability errors | X11 plus named GNOME/KDE/wlroots configurations pass; unsupported configurations are documented, not silently advertised |
| F. Release | Signed APK/desktop packages, pinned native artifacts and target-specific test reports | Clean installs work offline, permissions are understandable, rollback exists and 30-minute controlled-board runs have no double moves/unbounded growth |

### Tests that establish automation parity

* Unit tests use recording backends to verify one input intent per action, correct ordering, button release, cancellation IDs, callback handling, and coordinate math.
* Platform integration tests use real native event delivery and screenshot capture; mocks cannot prove a Wayland compositor grants permission or a phone receives a touch.
* Use a controlled local board that can log received pointer/touch events and expected legal positions. Test click/drag, captures, black/white orientation, small/large zoom, resize/rotation and both castling sides/colors.
* Add auto-queen and all underpromotions, delayed/cancelled gestures, opponent replies during verification, interrupted capture and Stop in every pipeline state.
* A timeout following a completed move must never cause a second move. API delivery success with no visual board change must never be reported as confirmed.
* Measure frame-to-position, analysis, dispatch/callback and verification separately. Optimize redundant capture/model work before shortening interaction timings. The extra platform hop through JNI is a measurement item, not a reason to run chess logic in the Android UI thread.

All native library/API choices still need the compilation and device/compositor checks above. The existing 32 Python tests remain the baseline but do not verify these new backends.

## Resulting user experience

PC: open ChessPilot, choose the capture source and color/orientation, calibrate if necessary, then use Play or Auto with an immediately available Stop. Wayland presents its system sharing/control approval where required.

Android: enable the input service, approve capture, open the target board, then use compact floating Play/Auto/Stop controls. The dashboard can remain in the background. Losing a required capability pauses the session with a specific recovery message. No PC connection, Python environment, or root privilege is part of the planned normal Android workflow.

The OS-facing pieces differ; the chess decisions, move history, detection policy, action scheduling, verification and UI meaning stay shared. Planning documents were updated only; no new backend or device/compositor automation was executed for this task.
