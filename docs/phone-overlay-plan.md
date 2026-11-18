# Phone controls

The phone uses a small movable overlay while the full Flutter app holds setup and settings. The PC window stays at 380×520. The implementation is connected in `PhoneOverlay.kt` and the Rust Android bridge; limited physical-phone results and remaining acceptance checks are recorded in [Android testing](../android-testing.md).

| Surface | Size and contents | Behavior |
| --- | --- | --- |
| Collapsed | 48×48 dp bubble with the existing app logo | Drag to reposition. Tap to expand when idle. While working, replace the logo with a white Stop square on red; one tap stops immediately. |
| Expanded | 216 dp wide, about 111 dp tall at normal text scale | Color/depth and status get separate lines beside a single quiet Collapse icon. A divider separates evenly spaced Play / Auto / Stop / Exit controls. Tap metadata or status to open the app. Minimum 48 dp touch targets; stack buttons vertically for large text. |
| Full app | Available phone screen | Color, depth, delay, move mode, castling, capture/touch permissions and detailed errors. No sliders or long menus in the overlay. |

The overlay uses the green/dark palette, a round collapsed bubble and rounded action buttons with pressed/disabled feedback. Play is the primary action; Auto highlights when selected without changing its label width. Stop uses muted red, and Exit remains separate from Stop. Status is a short label such as “Waiting”, “Working”, or “Ready”; tapping it shows details. Auto can play and verify the first move on the selected side’s turn, then use the same legal-reply baseline as PC; it can also resume after a verified manual move. Collapsing never stops an active operation, and expanding never starts one. Dragging pauses automation to avoid competing with the user's finger. Opening the dashboard also pauses it and hides the overlay.

## Placement and input

Use an Android accessibility overlay owned by the already-required touch service. It should not require a second general draw-over-apps permission. Keep the window non-focusable and touchable only inside its visible bounds. Drag from the bubble or panel header; buttons do not initiate dragging. Snap within the usable display edges, respecting cutouts and system insets. Remember the chosen edge/relative position, not coordinates from an old rotation.

Prefer a screen edge outside the board. Record the overlay's actual screen bounds in physical pixels. Reject a tap/drag whose path intersects those controls, including if the user moves the panel while analysis is running. The capture pipeline must hide/exclude/mask the controls consistently and reobserve before dispatch; merely making them transparent is insufficient. A board hidden by the panel should ask the user to move it.

Stop remains visible while working, including in the collapsed state. Keep the notification Stop action as another route. A tap on Stop cancels queued work immediately; an Android gesture already accepted by the system may finish, so wait for its callback and do not schedule a following tap. Stopping does not silently restart after activity recreation, permission loss, lock or process death.

## Implementation order

1. Shared Rust capture/gesture bridge and Android foreground/accessibility lifecycle: implemented, with broker tests and service compilation.
2. Bubble/panel in the accessibility service connected to the process-owned Rust session: implemented. It reads native snapshots and owns no second set of chess settings.
3. Overlay bounds protection, explicit capture masking, board-overlap rejection and drag/inset handling: connected in code. Fresh-frame and no-input-through-controls behavior still require device acceptance.
4. Verify on two physical phones: small portrait screen, landscape, large text, gesture navigation, cutouts, keyboard, app backgrounding and screen-sharing revocation. Check both move modes, no duplicate dispatch, stop during every state and no touch on ChessPilot controls.

The full settings window is not used as the overlay. Notification controls remain another route to Play / Stop moves / Exit. The compact overlay is included in the engineering build; only claim the physical cases actually recorded in the testing document.
