# Migration source inventory

Snapshot: `cbe8566d39953a510e20748e6d53165a78822f91`; prepared 12 November 2026.

Companion to [the Android/PC implementation plan](android-pc-migration-plan.md). Every authored Python source/test file was read, including its module-level code. This AST-generated index prevents omissions in the callable list and records the exact files read; it does not substitute for runtime verification.

The [automation plan](automation-plan.md) gives the concrete Windows, X11, Wayland and Android adapters behind the runtime/input and capture destinations in this inventory.

Counts: **38 source files / 6,136 lines; 6 test files / 413 lines; 324 named functions/methods, 23 classes, 61 lambdas**. Line counts include blank lines and comments. All symbol ranges below are inclusive and refer to this snapshot. Destination names are proposed, not existing Rust files.

Each section disposition also applies to imports, constants, style strings, top-level statements and main-guard/demo code outside the listed symbols. UI demonstration/CLI guards become fixtures or development entry points only if still useful; production startup is explicit. Callbacks inherit the containing operation and are replaced by typed Flutter events/native lifecycle handlers rather than copied as Python-style closures.

## `src/board_detection/__init__.py`

14 lines; SHA-256 `835e1754b94fe3698b7d544499f9682d34ea6439a1a2f7cada4b6dc0ca944971`.

**Destination:** Replace exports.

Export the runtime vision API; remove eager desktop/UI-dependent package imports.

No callable definitions; constants/exports/module body follow the file disposition.

## `src/board_detection/board_reader.py`

45 lines; SHA-256 `0af5c85802d88fb3f29c09442998cefbb88c526f58efa8514c66b7bd1f49f660`.

**Destination:** runtime/capture + runtime/vision.rs.

Replace screenshot-bound FEN wrappers with a frame observation API shared by native platforms; keep caller-visible typed failure/retry semantics.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 14-40 | function/method | `capture_and_extract_fen` | runtime/capture + runtime/vision.rs |
| 43-45 | function/method | `get_current_fen` | runtime/capture + runtime/vision.rs |

## `src/board_detection/fen_extractor.py`

118 lines; SHA-256 `09cdc8461fa2c0946f0d9d6fbdbdc2d355349e3e652636d30856c625b496967f`.

**Destination:** core/position.rs + core/geometry.rs.

Port confidence-grid placement and orientation transform; validate geometry/classes/position, keep turn independent, and replace fabricated history metadata.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 7-92 | function/method | `get_fen_from_position` | core/position.rs + core/geometry.rs |
| 94-98 | function/method | `flip_board` | core/position.rs + core/geometry.rs |

## `src/board_detection/get_positions.py`

171 lines; SHA-256 `ed8f7e36034d139f1a36c14caad72e829baa47d0a49a4bea278325f1586f4531`.

**Destination:** runtime/vision.rs.

Port tensor/output geometry and normal/refined search into a persistent native inference service; add observation budgets, ROI caching and model-contract checks.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 20-33 | function/method | `get_session` | runtime/vision.rs |
| 35-54 | function/method | `letterbox_resize` | runtime/vision.rs |
| 56-64 | function/method | `preprocess_image` | runtime/vision.rs |
| 66-78 | function/method | `scale_bbox` | runtime/vision.rs |
| 80-102 | function/method | `predict` | runtime/vision.rs |
| 104-109 | function/method | `_predict_region` | runtime/vision.rs |
| 112-128 | function/method | `_refine_board` | runtime/vision.rs |
| 131-167 | function/method | `get_positions` | runtime/vision.rs |

## `src/board_detection/model_classes.py`

25 lines; SHA-256 `d034c375d7ea8fc62ddc5d7f33b7585927d82a90855bd7e22d047d919eb4b044`.

**Destination:** runtime/vision.rs model contract.

Preserve all thirteen class IDs and four-piece promotion groups; version alongside the model.

No callable definitions; constants/exports/module body follow the file disposition.

## `src/core/__init__.py`

4 lines; SHA-256 `fa9a56ac31cdebb8b651774c5e457689114efcc5217d19908fdf94dd00dfe06a`.

**Destination:** Replace exports.

Expose pure domain API without screenshot or GUI imports.

No callable definitions; constants/exports/module body follow the file disposition.

## `src/core/board_utils.py`

43 lines; SHA-256 `53e3d335ded465ef8b4d68efca6c795bee3c90bda0450380da7edf9dbf7e8627`.

**Destination:** core/position.rs + core/geometry.rs.

Use validated square/position types; keep screen mapping, remove duplicate FEN expansion and capture re-export.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 4-12 | function/method | `expand_row` | Replace with validated board-library parsing; no parallel FEN parser |
| 15-21 | function/method | `fen_to_list` | core/position.rs: validated 64-square representation |
| 24-32 | function/method | `algebraic_to_index` | core/position.rs: typed square parse; invalid input is an error |
| 34-43 | function/method | `store_board_positions` | core/position.rs + core/geometry.rs |

## `src/core/config.py`

38 lines; SHA-256 `77d438c5117a0d2b0d41054baf6fc74680e52b6ec7850b91fb41441774beae57`.

**Destination:** core settings + Flutter theme + build metadata.

Separate analysis/runtime settings, presentation colors, version metadata and retry limits. Change uncertain-action handling from success to a distinct outcome.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 1-38 | class | `AppConfig` | core settings + Flutter theme + build metadata |

## `src/core/fen_utils.py`

192 lines; SHA-256 `9f19ab495793b60f256650cf7c96f0d902e6aecd9de289df64cacd79ef96f469`.

**Destination:** core/position.rs.

Use a legal-position library and explicit initial metadata; remove king/rook-position rights inference and GUI-variable adapters.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 9-16 | function/method | `expand_fen_row` | core/position.rs |
| 19-44 | function/method | `is_castling_possible` | core/position.rs |
| 47-88 | function/method | `is_two_square_king_move` | core/position.rs |
| 91-103 | function/method | `update_fen_castling_rights` | core/position.rs |
| 106-111 | function/method | `_validate_and_parse_fen` | core/position.rs |
| 114-119 | function/method | `_build_castling_rights` | core/position.rs |
| 122-132 | function/method | `_get_color_castling_rights` | core/position.rs |
| 135-139 | function/method | `_get_castling_symbols` | core/position.rs |
| 142-149 | function/method | `_should_add_castling_right` | core/position.rs |
| 152-184 | function/method | `_get_var_value` | Remove Qt/callable compatibility; bridge receives typed settings |
| 187-192 | function/method | `_reconstruct_fen_with_castling` | core/position.rs |

## `src/core/game_state.py`

42 lines; SHA-256 `9df9080032855ccc3641b75fd97db2670e3b0095c31f3e5089c6fc592266f4c4`.

**Destination:** core/session.rs.

Merge into one authoritative session, including geometry and observed/predicted/confirmed position; no duplicate window fields.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 5-42 | class | `GameState` | core/session.rs |
| 6-15 | function/method | `GameState.__init__` | core/session.rs |
| 17-21 | function/method | `GameState.update_last_fen_for_color` | core/session.rs |
| 23-25 | function/method | `GameState.set_color` | core/session.rs |
| 27-29 | function/method | `GameState.set_move_mode` | core/session.rs |
| 31-42 | function/method | `GameState.store_board_positions` | core/session.rs |

## `src/core/notation.py`

49 lines; SHA-256 `e7a622ce0304f5b64eef352957cbf1c873bd1275c639f9f7b446994fc7fe8b92`.

**Destination:** core/position.rs + core/geometry.rs.

Use validated UCI moves and separate orientation mapping; remove Qt dialogs and auto-mode side effects from conversion.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 7-49 | function/method | `chess_notation_to_index` | core/position.rs + core/geometry.rs |
| 34-34 | lambda | `chess_notation_to_index.<lambda 1>` | Replace callback as part of core/position.rs + core/geometry.rs |
| 38-43 | function/method | `chess_notation_to_index._turn_off` | core/position.rs + core/geometry.rs |

## `src/game/__init__.py`

6 lines; SHA-256 `1335f0d4fc14ba130be421526d6c567c31c83a1fa93360f3b96c59352a48faea`.

**Destination:** Replace exports.

Expose session commands; remove facade classes that only forward arguments.

No callable definitions; constants/exports/module body follow the file disposition.

## `src/game/auto_play.py`

385 lines; SHA-256 `b63d81e1c8d3763a5a39857e6bd8b4685865c5942d77da0424288b8c985a3b52`.

**Destination:** core/session.rs + runtime controller.

Replace polling threads and global counters with a single cancellable session; derive turns from known legal history, preserve settle/retry/stop behavior.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 18-50 | function/method | `_get_var_value` | Remove GUI-variable compatibility; use session settings |
| 53-76 | function/method | `_set_var_value` | Remove reflection-based mutation; emit typed state events |
| 79-111 | function/method | `process_move_thread` | Merge into the single runtime command queue; no detached daemon |
| 114-143 | function/method | `auto_move_loop` | core/session.rs + runtime controller |
| 146-164 | function/method | `_perform_initial_seeding` | core/session.rs + runtime controller |
| 167-179 | function/method | `_extract_fen_from_boxes` | core/session.rs + runtime controller |
| 182-185 | function/method | `_update_seed_positions` | core/session.rs + runtime controller |
| 188-250 | function/method | `_run_move_detection_loop` | core/session.rs + runtime controller |
| 253-272 | function/method | `_stop_auto_mode` | core/session.rs + runtime controller |
| 260-268 | function/method | `_stop_auto_mode._update_ui` | core/session.rs + runtime controller |
| 275-286 | function/method | `_should_continue_processing` | core/session.rs + runtime controller |
| 289-309 | function/method | `_capture_current_position` | core/session.rs + runtime controller |
| 311-326 | function/method | `_parse_fen_position` | core/session.rs + runtime controller |
| 328-332 | function/method | `_handle_opponent_turn` | core/session.rs + runtime controller |
| 334-344 | function/method | `_handle_player_turn` | core/session.rs + runtime controller |
| 346-371 | function/method | `_process_detected_move` | core/session.rs + runtime controller |
| 373-385 | class | `AutoPlayController` | core/session.rs + runtime controller |
| 375-385 | function/method | `AutoPlayController.start_auto_play` | Merge forwarding facade into runtime set_auto command |

## `src/game/move_execution.py`

327 lines; SHA-256 `21a4f386fe27b48e255837e6e25d5c002f3899c6d306ae1ed56fcf76c9436b4a`.

**Destination:** runtime/input + core/verification.rs.

Port native click/drag behavior behind capability-specific adapters; replace swallowed input failures and unverified-success outcomes with typed results.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 27-130 | class | `MoveExecutionMethods` | runtime/input + core/verification.rs |
| 29-36 | function/method | `MoveExecutionMethods._safe_disable_auto_mode` | runtime/input + core/verification.rs |
| 31-35 | function/method | `MoveExecutionMethods._safe_disable_auto_mode._turn_off` | runtime/input + core/verification.rs |
| 39-85 | function/method | `MoveExecutionMethods.drag_piece` | runtime/input + core/verification.rs |
| 84-84 | lambda | `MoveExecutionMethods.drag_piece.<lambda 1>` | Replace callback as part of runtime/input + core/verification.rs |
| 88-130 | function/method | `MoveExecutionMethods.click_piece` | runtime/input + core/verification.rs |
| 129-129 | lambda | `MoveExecutionMethods.click_piece.<lambda 2>` | Replace callback as part of runtime/input + core/verification.rs |
| 132-327 | class | `MoveExecutor` | runtime/input + core/verification.rs |
| 134-157 | function/method | `MoveExecutor.move_piece` | runtime/input + core/verification.rs |
| 144-144 | lambda | `MoveExecutor.move_piece.<lambda 3>` | Replace callback as part of runtime/input + core/verification.rs |
| 160-163 | function/method | `MoveExecutor.execute_move` | runtime/input + core/verification.rs |
| 166-168 | function/method | `MoveExecutor.convert_move_to_indices` | runtime/input + core/verification.rs |
| 171-173 | function/method | `MoveExecutor.relocate_cursor_to_button` | runtime/input + core/verification.rs |
| 176-209 | function/method | `MoveExecutor.execute_normal_move` | runtime/input + core/verification.rs |
| 212-251 | function/method | `MoveExecutor._attempt_single_move` | runtime/input + core/verification.rs |
| 254-263 | function/method | `MoveExecutor._get_move_positions` | runtime/input + core/verification.rs |
| 266-269 | function/method | `MoveExecutor._execute_physical_move` | runtime/input + core/verification.rs |
| 272-287 | function/method | `MoveExecutor._verify_move_execution` | runtime/input + core/verification.rs |
| 290-295 | function/method | `MoveExecutor._handle_successful_move` | runtime/input + core/verification.rs |
| 298-303 | function/method | `MoveExecutor._handle_unverified_move` | core/session.rs: uncertain result pauses auto; do not report success |
| 306-308 | function/method | `MoveExecutor._handle_move_failure` | runtime/input + core/verification.rs |
| 311-327 | function/method | `MoveExecutor._disable_auto_mode` | runtime/input + core/verification.rs |
| 316-323 | function/method | `MoveExecutor._disable_auto_mode._update_ui` | runtime/input + core/verification.rs |

## `src/game/move_processor.py`

377 lines; SHA-256 `f0661c2fc61f5b18e05d7f1de18113dab59961252f227c457469c59ecb9f25c5`.

**Destination:** runtime controller + core/session.rs.

Merge the manual/auto orchestration paths; keep analysis/execution/verification stages, commit only confirmed state and cancel stale work.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 19-55 | function/method | `process_move` | runtime controller + core/session.rs |
| 38-38 | lambda | `process_move.<lambda 1>` | Replace callback as part of runtime controller + core/session.rs |
| 39-39 | lambda | `process_move.<lambda 2>` | Replace callback as part of runtime controller + core/session.rs |
| 57-61 | function/method | `_can_start_processing` | Replace with session ownership; not a second lock/event check |
| 63-66 | function/method | `_initialize_move_processing` | Merge into controller state entry; remove duplicated initializer |
| 65-65 | lambda | `_initialize_move_processing.<lambda 3>` | Replace callback as part of runtime controller + core/session.rs |
| 66-66 | lambda | `_initialize_move_processing.<lambda 4>` | Replace callback as part of runtime controller + core/session.rs |
| 68-107 | function/method | `_extract_board_position` | runtime controller + core/session.rs |
| 83-83 | lambda | `_extract_board_position.<lambda 5>` | Replace callback as part of runtime controller + core/session.rs |
| 87-87 | lambda | `_extract_board_position.<lambda 6>` | Replace callback as part of runtime controller + core/session.rs |
| 109-137 | function/method | `_extract_fen_from_boxes` | runtime controller + core/session.rs |
| 114-114 | lambda | `_extract_fen_from_boxes.<lambda 7>` | Replace callback as part of runtime controller + core/session.rs |
| 116-116 | lambda | `_extract_fen_from_boxes.<lambda 8>` | Replace callback as part of runtime controller + core/session.rs |
| 132-132 | lambda | `_extract_fen_from_boxes.<lambda 9>` | Replace callback as part of runtime controller + core/session.rs |
| 139-159 | function/method | `_process_best_move` | runtime controller: keep predicted state separate until verified |
| 161-171 | function/method | `_prepare_position_data` | runtime controller + core/session.rs |
| 173-185 | function/method | `_calculate_best_move` | runtime controller + core/session.rs |
| 180-180 | lambda | `_calculate_best_move.<lambda 10>` | Replace callback as part of runtime controller + core/session.rs |
| 183-183 | lambda | `_calculate_best_move.<lambda 11>` | Replace callback as part of runtime controller + core/session.rs |
| 187-204 | function/method | `_execute_move` | runtime controller + core/session.rs |
| 206-209 | function/method | `_should_execute_castling` | runtime controller + core/session.rs |
| 211-221 | function/method | `_execute_castling_move` | runtime controller + core/session.rs |
| 223-232 | function/method | `_auto_enable_castling_checkbox` | runtime controller + core/session.rs |
| 229-229 | lambda | `_auto_enable_castling_checkbox.<lambda 12>` | Replace callback as part of runtime controller + core/session.rs |
| 232-232 | lambda | `_auto_enable_castling_checkbox.<lambda 13>` | Replace callback as part of runtime controller + core/session.rs |
| 234-268 | function/method | `_perform_castling_move` | runtime controller + core/session.rs |
| 270-300 | function/method | `_execute_castling_pieces` | runtime/input: king action; inspect rook before any fallback action |
| 302-320 | function/method | `_verify_castling_execution` | runtime controller + core/session.rs |
| 322-329 | function/method | `_handle_successful_castling` | runtime controller + core/session.rs |
| 331-336 | function/method | `_handle_unverified_castling` | core/session.rs: uncertain result pauses auto; reacquire before retry |
| 338-340 | function/method | `_handle_castling_failure` | runtime controller + core/session.rs |
| 342-358 | function/method | `_disable_auto_mode` | runtime controller + core/session.rs |
| 347-354 | function/method | `_disable_auto_mode._update_ui` | runtime controller + core/session.rs |
| 360-366 | function/method | `_handle_processing_error` | runtime controller + core/session.rs |
| 362-362 | lambda | `_handle_processing_error.<lambda 14>` | Replace callback as part of runtime controller + core/session.rs |
| 368-377 | function/method | `_finalize_move_processing` | runtime controller + core/session.rs |
| 377-377 | lambda | `_finalize_move_processing.<lambda 15>` | Replace callback as part of runtime controller + core/session.rs |

## `src/game/move_validator.py`

167 lines; SHA-256 `e885789f53971265adcbde1c10475a168538f93345202972c6d61819fd4e3824`.

**Destination:** core/verification.rs.

Replace incomplete placement comparisons with complete legal expected transitions; separate live capture retry from pure verification.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 9-167 | class | `MoveValidator` | core/verification.rs |
| 11-65 | function/method | `MoveValidator.did_my_piece_move` | core/verification.rs |
| 68-103 | function/method | `MoveValidator.did_castling_move` | core/verification.rs |
| 106-108 | function/method | `MoveValidator.check_move_validity` | core/verification.rs |
| 111-167 | function/method | `MoveValidator.verify_move` | Split pure expected-transition check from runtime frame acquisition |

## `src/game/promotion.py`

200 lines; SHA-256 `5574ee56640b5b1557ce31cd6f9bf3945017718a61f91a49642546cdaf5cfb4c`.

**Destination:** runtime/input promotion + runtime/vision.rs.

Keep raw detections and all four pieces; isolate menu candidates from ordinary board pieces and verify auto-queen/underpromotion outcomes.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 21-62 | function/method | `detect_promotion_pieces` | runtime/input promotion + runtime/vision.rs |
| 64-67 | function/method | `find_promotion_dialog_pieces` | runtime/input promotion + runtime/vision.rs |
| 66-66 | lambda | `find_promotion_dialog_pieces.<lambda 1>` | Replace callback as part of runtime/input promotion + runtime/vision.rs |
| 69-96 | function/method | `select_promotion_piece` | runtime/input promotion + runtime/vision.rs |
| 98-101 | function/method | `is_pawn_promotion_move` | runtime/input promotion + runtime/vision.rs |
| 103-106 | function/method | `get_promotion_piece_from_move` | runtime/input promotion + runtime/vision.rs |
| 108-110 | function/method | `is_promotion_dialog_visible` | runtime/input promotion + runtime/vision.rs |
| 112-145 | function/method | `wait_for_promotion_dialog` | runtime/input promotion + runtime/vision.rs |
| 147-200 | function/method | `handle_pawn_promotion` | runtime/input promotion + runtime/vision.rs |

## `src/gui/__init__.py`

29 lines; SHA-256 `1f0754ea2fbe494980ec2fe8a0b1d84f0c149534127bff8f21abe5f90eb97420`.

**Destination:** Flutter lib/ exports.

Replace PyQt export surface; keep product actions, not widget factories.

No callable definitions; constants/exports/module body follow the file disposition.

## `src/gui/button_and_checkboxes.py`

173 lines; SHA-256 `8bff70b6256e5d61a76a5790b12aadb045f21bcbd56b396b789fd1cde5d21cb4`.

**Destination:** Flutter lib/ controls + theme.

Replace fixed-pixel Qt widgets/styles with accessible responsive Flutter controls; preserve color/mode/castling/shortcuts actions and branding.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 7-30 | function/method | `color_button` | Flutter lib/ controls + theme |
| 29-29 | lambda | `color_button.<lambda 1>` | Replace callback as part of Flutter lib/ controls + theme |
| 32-58 | function/method | `action_button` | Flutter lib/ controls + theme |
| 60-85 | function/method | `shortcuts_button` | Flutter lib/ controls + theme |
| 87-132 | function/method | `castling_checkboxes` | Flutter lib/ controls + theme |
| 108-108 | lambda | `castling_checkboxes.<lambda 2>` | Replace callback as part of Flutter lib/ controls + theme |
| 130-130 | lambda | `castling_checkboxes.<lambda 3>` | Replace callback as part of Flutter lib/ controls + theme |
| 134-157 | function/method | `move_mode` | Flutter lib/ controls + theme |
| 156-156 | lambda | `move_mode.<lambda 4>` | Replace callback as part of Flutter lib/ controls + theme |
| 160-173 | function/method | `set_window_icon` | Flutter lib/ controls + theme |

## `src/gui/create_widget.py`

454 lines; SHA-256 `3a421d0ab1eee50b1322ebe892102fc14c9ad5237d4975eda5a40c4a4568be13`.

**Destination:** Flutter lib/ screens + settings.

Replace selection/play widget trees with a responsive screen and compact controls; unify depth state instead of synchronizing duplicated sliders.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 9-13 | function/method | `update_depth_label` | Flutter lib/ screens + settings |
| 15-454 | function/method | `create_widgets` | Flutter lib/ screens + settings |
| 41-41 | lambda | `create_widgets.<lambda 1>` | Replace callback as part of Flutter lib/ screens + settings |
| 200-200 | lambda | `create_widgets.<lambda 2>` | Replace callback as part of Flutter lib/ screens + settings |
| 245-245 | lambda | `create_widgets.<lambda 3>` | Replace callback as part of Flutter lib/ screens + settings |
| 267-267 | lambda | `create_widgets.<lambda 4>` | Replace callback as part of Flutter lib/ screens + settings |
| 298-298 | lambda | `create_widgets.<lambda 5>` | Replace callback as part of Flutter lib/ screens + settings |
| 358-358 | lambda | `create_widgets.<lambda 6>` | Replace callback as part of Flutter lib/ screens + settings |
| 439-449 | function/method | `create_widgets.sync_depth_sliders` | Flutter lib/ screens + settings |

## `src/gui/download_dialog.py`

149 lines; SHA-256 `1d51f7aea1196ab56eecfd8e16c871e084dbb19f0118527010f7a97846720577`.

**Destination:** Flutter lib/ resource-status UI.

Replace Qt signals and nested app-loop workflow with typed progress events; keep progress, errors and user retry.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 18-24 | class | `ProgressSignals` | Flutter lib/ resource-status UI |
| 27-149 | class | `StockfishDownloaderApp` | Flutter lib/ resource-status UI |
| 29-49 | function/method | `StockfishDownloaderApp.__init__` | Flutter lib/ resource-status UI |
| 51-90 | function/method | `StockfishDownloaderApp._setup_styles` | Flutter lib/ resource-status UI |
| 92-117 | function/method | `StockfishDownloaderApp._create_widgets` | Flutter lib/ resource-status UI |
| 119-120 | function/method | `StockfishDownloaderApp._update_label` | Flutter lib/ resource-status UI |
| 122-123 | function/method | `StockfishDownloaderApp._update_sub_label` | Flutter lib/ resource-status UI |
| 125-126 | function/method | `StockfishDownloaderApp._update_progress` | Flutter lib/ resource-status UI |
| 128-129 | function/method | `StockfishDownloaderApp._show_retry_button` | Flutter lib/ resource-status UI |
| 131-136 | function/method | `StockfishDownloaderApp._close_after` | Flutter lib/ resource-status UI |
| 138-141 | function/method | `StockfishDownloaderApp._retry_download` | Flutter lib/ resource-status UI |
| 143-149 | function/method | `StockfishDownloaderApp._start_download_flow` | Flutter lib/ resource-status UI |

## `src/gui/shortcuts.py`

123 lines; SHA-256 `2e1d0632177d3bc24374abbd849e107a6a5c971987f340cfa317c1feaec19150`.

**Destination:** Flutter lib/ desktop shortcuts + session commands.

Preserve key actions/mode rules; Android gets touch equivalents; stop must cancel old work, not just hide a frame.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 7-18 | function/method | `handle_esc_key` | Flutter lib/ desktop shortcuts + session commands |
| 20-25 | function/method | `set_color_with_safeguard` | Flutter lib/ desktop shortcuts + session commands |
| 27-81 | function/method | `bind_shortcuts` | Flutter lib/ desktop shortcuts + session commands |
| 30-30 | lambda | `bind_shortcuts.<lambda 1>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 35-35 | lambda | `bind_shortcuts.<lambda 2>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 38-38 | lambda | `bind_shortcuts.<lambda 3>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 43-43 | lambda | `bind_shortcuts.<lambda 4>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 46-46 | lambda | `bind_shortcuts.<lambda 5>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 51-51 | lambda | `bind_shortcuts.<lambda 6>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 56-56 | lambda | `bind_shortcuts.<lambda 7>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 61-61 | lambda | `bind_shortcuts.<lambda 8>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 64-64 | lambda | `bind_shortcuts.<lambda 9>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 69-69 | lambda | `bind_shortcuts.<lambda 10>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 72-72 | lambda | `bind_shortcuts.<lambda 11>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 77-77 | lambda | `bind_shortcuts.<lambda 12>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 80-80 | lambda | `bind_shortcuts.<lambda 13>` | Replace callback as part of Flutter lib/ desktop shortcuts + session commands |
| 83-88 | function/method | `adjust_delay_up` | Flutter lib/ desktop shortcuts + session commands |
| 90-95 | function/method | `adjust_delay_down` | Flutter lib/ desktop shortcuts + session commands |
| 97-102 | function/method | `adjust_depth_up` | Flutter lib/ desktop shortcuts + session commands |
| 104-109 | function/method | `adjust_depth_down` | Flutter lib/ desktop shortcuts + session commands |
| 111-123 | function/method | `set_mode_shortcut` | Flutter lib/ desktop shortcuts + session commands |

## `src/gui/shortcuts_dialog.py`

211 lines; SHA-256 `07b86c8b5aa9d087ae6f4165c23149e8f2c4ee4ee4e8c554bf6823584f92e98e`.

**Destination:** Flutter lib/ help + diagnostics.

Preserve shortcut help/log export/open action; replace platform-specific folder behavior as appropriate.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 17-206 | class | `ShortcutsDialog` | Flutter lib/ help + diagnostics |
| 18-153 | function/method | `ShortcutsDialog.__init__` | Flutter lib/ help + diagnostics |
| 155-158 | function/method | `ShortcutsDialog._open_logs_folder` | Flutter lib/ help + diagnostics |
| 160-206 | function/method | `ShortcutsDialog._create_shortcuts_table` | Flutter lib/ help + diagnostics |
| 208-211 | function/method | `show_shortcuts_dialog` | Flutter lib/ help + diagnostics |

## `src/main.py`

293 lines; SHA-256 `d8ac49b56924e5d5f0e19fdfa4981ec627cd2b33fc859be412cf41421827425c`.

**Destination:** Flutter runners + runtime/api.rs.

Replace import-time chdir/resource/Qt setup and daemon thread launch; initialize services explicitly, share one state owner, stop/join on shutdown.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 83-258 | class | `ChessPilot` | Flutter runners + runtime/api.rs |
| 84-162 | function/method | `ChessPilot.__init__` | Flutter runners + runtime/api.rs |
| 164-165 | function/method | `ChessPilot.create_color_button` | Remove forwarding wrapper; Flutter uses direct reusable controls |
| 167-168 | function/method | `ChessPilot.create_action_button` | Remove forwarding wrapper; Flutter uses direct reusable controls |
| 170-171 | function/method | `ChessPilot.create_move_method_radiobuttons` | Remove forwarding wrapper; Flutter uses direct reusable controls |
| 173-174 | function/method | `ChessPilot.create_castling_checkboxes` | Remove forwarding wrapper; Flutter uses direct reusable controls |
| 176-177 | function/method | `ChessPilot.create_shortcuts_button` | Remove forwarding wrapper; Flutter uses direct reusable controls |
| 179-186 | function/method | `ChessPilot.set_color` | Flutter runners + runtime/api.rs |
| 188-192 | function/method | `ChessPilot.set_move_mode` | Flutter runners + runtime/api.rs |
| 194-197 | function/method | `ChessPilot.update_status` | Flutter UI event subscription; UI isolate owns widgets |
| 199-218 | function/method | `ChessPilot.process_move_thread` | runtime play_next command; no duplicated thread bootstrap |
| 206-206 | lambda | `ChessPilot.process_move_thread.<lambda 1>` | Replace callback as part of Flutter runners + runtime/api.rs |
| 211-211 | lambda | `ChessPilot.process_move_thread.<lambda 2>` | Replace callback as part of Flutter runners + runtime/api.rs |
| 212-212 | lambda | `ChessPilot.process_move_thread.<lambda 3>` | Replace callback as part of Flutter runners + runtime/api.rs |
| 215-215 | lambda | `ChessPilot.process_move_thread.<lambda 4>` | Replace callback as part of Flutter runners + runtime/api.rs |
| 220-245 | function/method | `ChessPilot.toggle_auto_mode` | runtime set_auto command; cancellation on disable |
| 230-230 | lambda | `ChessPilot.toggle_auto_mode.<lambda 5>` | Replace callback as part of Flutter runners + runtime/api.rs |
| 235-235 | lambda | `ChessPilot.toggle_auto_mode.<lambda 6>` | Replace callback as part of Flutter runners + runtime/api.rs |
| 237-237 | lambda | `ChessPilot.toggle_auto_mode.<lambda 7>` | Replace callback as part of Flutter runners + runtime/api.rs |
| 238-238 | lambda | `ChessPilot.toggle_auto_mode.<lambda 8>` | Replace callback as part of Flutter runners + runtime/api.rs |
| 247-251 | function/method | `ChessPilot.closeEvent` | explicit stop/cancel/join lifecycle before engine/capture disposal |
| 253-258 | function/method | `ChessPilot.update_last_fen_for_color` | Flutter runners + runtime/api.rs |
| 269-269 | lambda | `<lambda 9>` | Replace callback as part of Flutter runners + runtime/api.rs |
| 272-274 | function/method | `sigint_handler` | Flutter runners + runtime/api.rs |

## `src/services/__init__.py`

3 lines; SHA-256 `9155c008f551a7520f7e22effe8334381059a9e327a5189f6909d227aa73a9d9`.

**Destination:** runtime engine API.

Replace the Python service export with an owned engine adapter.

No callable definitions; constants/exports/module body follow the file disposition.

## `src/services/engine_service.py`

403 lines; SHA-256 `dc1b42d4a2cf7109260f6ddca96e90ea58a2f288f96217b1713c72293076bdb4`.

**Destination:** runtime/engine + runtime/resources.rs.

Keep UCI protocol/config/progress/recovery intent; replace blocking IO, display-command FEN parsing and shared global engine lifetime. Android uses a bundled native library adapter.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 18-23 | function/method | `get_root_dir` | runtime/engine + runtime/resources.rs |
| 25-50 | function/method | `get_config_file_path` | runtime/engine + runtime/resources.rs |
| 54-72 | function/method | `create_default_config` | runtime/engine + runtime/resources.rs |
| 74-108 | function/method | `load_engine_config` | runtime/engine + runtime/resources.rs |
| 110-117 | function/method | `ensure_config_exists` | runtime/engine + runtime/resources.rs |
| 119-172 | function/method | `_initialize_stockfish` | runtime/engine + runtime/resources.rs |
| 174-202 | function/method | `_cleanup_stockfish` | runtime/engine + runtime/resources.rs |
| 204-217 | function/method | `_initialize_stockfish_at_startup` | runtime/engine + runtime/resources.rs |
| 219-227 | function/method | `_setup_stockfish_engine` | runtime/engine + runtime/resources.rs |
| 229-275 | function/method | `_get_move_from_engine` | runtime/engine: serialized async UCI search with real deadlines |
| 277-290 | function/method | `_check_for_mate` | Separate latest evaluation from legally determined game outcome |
| 292-297 | function/method | `_extract_best_move` | runtime/engine + runtime/resources.rs |
| 299-334 | function/method | `_get_updated_fen` | Replace Stockfish d-command parsing with core legal move application |
| 336-340 | function/method | `_handle_stockfish_failure` | runtime/engine + runtime/resources.rs |
| 342-346 | function/method | `_handle_error` | runtime/engine + runtime/resources.rs |
| 348-350 | function/method | `_show_error_dialog` | Remove Qt dialog; emit typed error for Flutter UI |
| 350-350 | lambda | `_show_error_dialog.<lambda 1>` | Replace callback as part of runtime/engine + runtime/resources.rs |
| 352-357 | function/method | `_disable_auto_mode` | runtime/engine + runtime/resources.rs |
| 359-402 | class | `EngineService` | runtime/engine + runtime/resources.rs |
| 361-363 | function/method | `EngineService.initialize` | runtime/engine + runtime/resources.rs |
| 366-368 | function/method | `EngineService.cleanup` | runtime/engine + runtime/resources.rs |
| 371-402 | function/method | `EngineService.get_best_move` | runtime/engine + runtime/resources.rs |

## `src/utils/__init__.py`

0 lines; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

**Destination:** Remove empty package.

No behavior to translate.

No callable definitions; constants/exports/module body follow the file disposition.

## `src/utils/chess_resources_manager.py`

332 lines; SHA-256 `cadc4aba0a00bc7c776bce890bf04237d01bdbf3681f80367b9569515955eaad`.

**Destination:** runtime/resources.rs.

Consolidate repeated path probes/downloader conventions; keep offline/manual resource import; avoid implicit movement of unrelated files.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 16-37 | function/method | `find_file_with_keyword` | runtime/resources.rs |
| 40-42 | function/method | `_get_stockfish_binary_name` | runtime/resources.rs |
| 45-56 | function/method | `_check_bundled_stockfish` | runtime/resources.rs |
| 59-63 | function/method | `_get_working_directory` | runtime/resources.rs |
| 66-74 | function/method | `_check_system_stockfish` | runtime/resources.rs |
| 77-82 | function/method | `_check_existing_stockfish` | runtime/resources.rs |
| 85-102 | function/method | `_download_and_handle_stockfish` | runtime/resources.rs |
| 105-123 | function/method | `_process_download_result` | runtime/resources.rs |
| 126-142 | function/method | `_handle_path_result` | runtime/resources.rs |
| 145-152 | function/method | `_set_executable_permissions` | runtime/resources.rs |
| 155-187 | function/method | `extract_stockfish` | runtime/resources.rs |
| 190-203 | function/method | `_check_bundled_onnx` | runtime/resources.rs |
| 206-217 | function/method | `_find_onnx_model` | runtime/resources.rs |
| 220-228 | function/method | `_move_onnx_model` | runtime/resources.rs |
| 231-264 | function/method | `rename_onnx_model` | runtime/resources.rs |
| 267-277 | function/method | `_move_resource_from_project_root` | runtime/resources.rs |
| 280-319 | function/method | `setup_resources` | runtime/resources.rs |

## `src/utils/cpu_features.py`

238 lines; SHA-256 `634e8d4d576d25102992b280194b650dcd7f3a2493da38b187e3b01c8769489f`.

**Destination:** runtime/resources.rs + diagnostics.

Use platform/ABI targets and proven CPU feature checks. Replace WMIC/default-AVX guesses and preserve diagnostic labels/byte formatting as useful.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 15-24 | function/method | `detect_os` | runtime/resources.rs + diagnostics |
| 27-33 | function/method | `format_bytes` | runtime/resources.rs + diagnostics |
| 36-60 | function/method | `detect_cpu_info` | runtime/resources.rs + diagnostics |
| 63-98 | function/method | `_detect_linux_cpu_info` | runtime/resources.rs + diagnostics |
| 101-118 | function/method | `_detect_mac_cpu_info` | runtime/resources.rs + diagnostics |
| 121-124 | function/method | `_detect_windows_cpu_info` | runtime/resources.rs + diagnostics |
| 127-136 | function/method | `_get_cpu_vendor` | runtime/resources.rs + diagnostics |
| 139-151 | function/method | `_try_cpuinfo_vendor` | runtime/resources.rs + diagnostics |
| 154-160 | function/method | `_try_platform_vendor` | runtime/resources.rs + diagnostics |
| 163-173 | function/method | `_try_wmic_vendor` | runtime/resources.rs + diagnostics |
| 176-184 | function/method | `_get_wmic_path` | runtime/resources.rs + diagnostics |
| 187-190 | function/method | `_run_wmic_command` | runtime/resources.rs + diagnostics |
| 193-198 | function/method | `_parse_vendor_from_string` | runtime/resources.rs + diagnostics |
| 201-206 | function/method | `_get_cpu_flags` | runtime/resources.rs + diagnostics |
| 209-218 | function/method | `_try_cpuinfo_flags` | runtime/resources.rs + diagnostics |
| 221-227 | function/method | `_get_default_windows_flags` | Replace optimistic guesses with guaranteed baseline/runtime detection |
| 230-232 | function/method | `_is_64bit_system` | runtime/resources.rs + diagnostics |
| 235-238 | function/method | `detect_arch_flags` | runtime/resources.rs + diagnostics |

## `src/utils/downloader.py`

589 lines; SHA-256 `c81f74c15abdae0377c780416a8adee213bda42b3309c46354beed229c154d1d`.

**Destination:** runtime/resources.rs + Flutter progress events.

Desktop-only resource install path with architecture filtering, hashes and atomic installation. Android bundles libraries. Preserve extraction safety/error handling; remove UI event-loop ownership.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 23-30 | function/method | `choose_best_asset` | runtime/resources.rs: exact OS/ABI/arch filter before instruction selection |
| 33-46 | function/method | `_filter_assets_by_os` | runtime/resources.rs + Flutter progress events |
| 49-52 | function/method | `_matches_os_prefix` | runtime/resources.rs + Flutter progress events |
| 55-58 | function/method | `_matches_os_generic` | runtime/resources.rs + Flutter progress events |
| 61-72 | function/method | `_select_best_by_cpu_features` | runtime/resources.rs + Flutter progress events |
| 75-122 | function/method | `_calculate_cpu_score` | runtime/resources.rs + Flutter progress events |
| 83-83 | lambda | `_calculate_cpu_score.<lambda 1>` | Replace callback as part of runtime/resources.rs + Flutter progress events |
| 89-89 | lambda | `_calculate_cpu_score.<lambda 2>` | Replace callback as part of runtime/resources.rs + Flutter progress events |
| 95-95 | lambda | `_calculate_cpu_score.<lambda 3>` | Replace callback as part of runtime/resources.rs + Flutter progress events |
| 101-101 | lambda | `_calculate_cpu_score.<lambda 4>` | Replace callback as part of runtime/resources.rs + Flutter progress events |
| 125-137 | function/method | `_check_instruction_sets` | runtime/resources.rs + Flutter progress events |
| 140-153 | function/method | `_calculate_vendor_bonus` | runtime/resources.rs + Flutter progress events |
| 156-168 | function/method | `_calculate_fallback_score` | runtime/resources.rs + Flutter progress events |
| 171-174 | function/method | `_calculate_format_bonus` | runtime/resources.rs + Flutter progress events |
| 177-187 | function/method | `_calculate_vendor_penalty` | runtime/resources.rs + Flutter progress events |
| 191-236 | function/method | `download_file` | runtime/resources.rs + Flutter progress events |
| 239-332 | class | `BinaryExtractor` | runtime/resources.rs + Flutter progress events |
| 240-242 | function/method | `BinaryExtractor.__init__` | runtime/resources.rs + Flutter progress events |
| 244-271 | function/method | `BinaryExtractor.extract_binary` | runtime/resources.rs + Flutter progress events |
| 273-274 | function/method | `BinaryExtractor._is_tar_archive` | runtime/resources.rs + Flutter progress events |
| 276-277 | function/method | `BinaryExtractor._is_zip_archive` | runtime/resources.rs + Flutter progress events |
| 279-292 | function/method | `BinaryExtractor._extract_tar` | runtime/resources.rs + Flutter progress events |
| 294-304 | function/method | `BinaryExtractor._extract_zip` | runtime/resources.rs + Flutter progress events |
| 306-309 | function/method | `BinaryExtractor._copy_single_file` | runtime/resources.rs + Flutter progress events |
| 311-315 | function/method | `BinaryExtractor._is_safe_path` | runtime/resources.rs + Flutter progress events |
| 317-322 | function/method | `BinaryExtractor._find_stockfish_binary` | runtime/resources.rs + Flutter progress events |
| 324-328 | function/method | `BinaryExtractor._set_binary_permissions` | runtime/resources.rs + Flutter progress events |
| 330-332 | function/method | `BinaryExtractor._cleanup` | runtime/resources.rs + Flutter progress events |
| 335-337 | function/method | `extract_binary` | runtime/resources.rs + Flutter progress events |
| 341-543 | class | `DownloadWorkflow` | runtime/resources.rs + Flutter progress events |
| 342-345 | function/method | `DownloadWorkflow.__init__` | runtime/resources.rs + Flutter progress events |
| 347-376 | function/method | `DownloadWorkflow.execute` | runtime/resources.rs + Flutter progress events |
| 378-387 | function/method | `DownloadWorkflow._is_already_installed` | runtime/resources.rs + Flutter progress events |
| 389-399 | function/method | `DownloadWorkflow._get_target_path` | runtime/resources.rs + Flutter progress events |
| 401-427 | function/method | `DownloadWorkflow._fetch_release_data` | runtime/resources.rs + Flutter progress events |
| 429-441 | function/method | `DownloadWorkflow._select_asset` | runtime/resources.rs + Flutter progress events |
| 443-462 | function/method | `DownloadWorkflow._download_asset` | runtime/resources.rs + Flutter progress events |
| 464-481 | function/method | `DownloadWorkflow._is_cached_and_valid` | runtime/resources.rs: hash-verified cache, not size alone |
| 483-493 | function/method | `DownloadWorkflow._create_progress_callback` | runtime/resources.rs + Flutter progress events |
| 484-492 | function/method | `DownloadWorkflow._create_progress_callback.progress_cb` | runtime/resources.rs + Flutter progress events |
| 495-507 | function/method | `DownloadWorkflow._extract_binary` | runtime/resources.rs + Flutter progress events |
| 509-516 | function/method | `DownloadWorkflow._install_binary` | runtime/resources.rs + Flutter progress events |
| 518-529 | function/method | `DownloadWorkflow._install_windows` | runtime/resources.rs + Flutter progress events |
| 531-543 | function/method | `DownloadWorkflow._install_unix` | runtime/resources.rs + Flutter progress events |
| 547-584 | function/method | `download_stockfish` | Desktop install command with progress; no Qt event loop; Android packaged library |

## `src/utils/get_binary_path.py`

31 lines; SHA-256 `4dfac8acbce337b91afbc894265b2d808b276941f2a0e3f92ca18960eeed4e86`.

**Destination:** runtime/resources.rs.

Return a typed missing-capability/resource error; never create a GUI dialog or exit the process inside path lookup.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 10-31 | function/method | `get_binary_path` | runtime/resources.rs |

## `src/utils/logging_setup.py`

160 lines; SHA-256 `b03495098a2df16300556aa88418162b7681ab50ad1009a3ca3198cded7915a7`.

**Destination:** runtime diagnostics + platform log storage.

Preserve rotation, bounded logs and error context; replace Python exception hooks with native panic/error and Flutter error reporting.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 20-35 | class | `ColorFormatter` | runtime diagnostics + platform log storage |
| 29-35 | function/method | `ColorFormatter.format` | runtime diagnostics + platform log storage |
| 38-80 | function/method | `get_log_dir` | runtime diagnostics + platform log storage |
| 83-85 | function/method | `get_log_file_path` | runtime diagnostics + platform log storage |
| 88-156 | function/method | `setup_logging` | runtime diagnostics + platform log storage |
| 132-139 | function/method | `setup_logging._handle_uncaught_exception` | runtime diagnostics + platform log storage |
| 144-151 | function/method | `setup_logging._handle_thread_exception` | runtime diagnostics + platform log storage |

## `src/utils/resource_path.py`

145 lines; SHA-256 `85d005ca344646e9ca00566e9ef7a7bda708016529fe455160d79ffc82a5c2c0`.

**Destination:** runtime/resources.rs.

One resolver for bundle, app-data and explicit user engine path; remove PyInstaller/CWD compatibility branches from the new runtime.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 13-19 | function/method | `_find_system_stockfish` | runtime/resources.rs |
| 22-38 | function/method | `_get_local_stockfish_candidates` | runtime/resources.rs |
| 41-50 | function/method | `_find_existing_candidate` | runtime/resources.rs |
| 53-88 | function/method | `_download_stockfish_with_fallback` | runtime/resources.rs |
| 91-109 | function/method | `_handle_stockfish_unix` | runtime/resources.rs |
| 112-124 | function/method | `_handle_frozen_app_resources` | runtime/resources.rs |
| 127-132 | function/method | `_handle_dev_resources` | runtime/resources.rs |
| 135-145 | function/method | `resource_path` | runtime/resources.rs |

## `src/utils/system_info.py`

130 lines; SHA-256 `c4aec61e54d7af8c1ad0b9a3d2ed7b734c41d4d9f7c224b25b4b80f3fabf6bdb`.

**Destination:** runtime diagnostics.

Preserve OS/architecture/runtime/provider/version information; replace Python dependency checks with compile/runtime capability checks.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 12-45 | function/method | `get_system_info` | runtime diagnostics |
| 48-76 | function/method | `log_system_info` | runtime diagnostics |
| 79-108 | function/method | `check_dependencies` | runtime diagnostics |
| 110-130 | function/method | `log_dependency_status` | runtime diagnostics |

## `src/utils/system_interaction.py`

203 lines; SHA-256 `61ba61a192529b2f289bd0e52d47434b96a36859f5a9cef3f559301a08daf7da`.

**Destination:** runtime/capture + runtime/input + Flutter diagnostics.

Separate capture, cursor placement, UI queries and error reporting; preserve monitor origin/DPI and Android service permissions; remove Qt dependencies.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 20-22 | class | `CursorMoveError` | runtime/capture + runtime/input + Flutter diagnostics |
| 25-27 | function/method | `is_wayland` | runtime/capture + runtime/input + Flutter diagnostics |
| 30-58 | function/method | `capture_screenshot_in_memory` | runtime/capture + runtime/input + Flutter diagnostics |
| 49-49 | lambda | `capture_screenshot_in_memory.<lambda 1>` | Replace callback as part of runtime/capture + runtime/input + Flutter diagnostics |
| 51-56 | function/method | `capture_screenshot_in_memory._turn_off` | runtime/capture + runtime/input + Flutter diagnostics |
| 61-80 | function/method | `get_button_info` | runtime/capture + runtime/input + Flutter diagnostics |
| 83-109 | function/method | `calculate_button_center` | runtime/capture + runtime/input + Flutter diagnostics |
| 112-136 | function/method | `move_cursor_platform_specific` | runtime/capture + runtime/input + Flutter diagnostics |
| 139-153 | function/method | `disable_auto_mode` | runtime/capture + runtime/input + Flutter diagnostics |
| 150-150 | lambda | `disable_auto_mode.<lambda 2>` | Replace callback as part of runtime/capture + runtime/input + Flutter diagnostics |
| 156-164 | function/method | `show_error_message` | runtime/capture + runtime/input + Flutter diagnostics |
| 159-162 | lambda | `show_error_message.<lambda 3>` | Replace callback as part of runtime/capture + runtime/input + Flutter diagnostics |
| 167-203 | function/method | `move_cursor_to_button` | runtime/capture + runtime/input + Flutter diagnostics |

## `src/wayland_capture/__init__.py`

1 lines; SHA-256 `7b9b0679e447246b2fbf434d18dd55d6c60329c429b28565d48d88685dfeaa4e`.

**Destination:** runtime Linux capability module.

Replace raw exported socket client with a negotiated native Linux adapter.

No callable definitions; constants/exports/module body follow the file disposition.

## `src/wayland_capture/screen.py`

21 lines; SHA-256 `8279cc92267e5350c54f570b7939eeee503de4d2561ae81595704f669055c2ec`.

**Destination:** runtime/capture/linux geometry.

Use structured monitor/capture metadata instead of parsing one output size or returning error strings as geometry.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 6-18 | function/method | `get_resolution` | runtime/capture/linux geometry |

## `src/wayland_capture/wayland.py`

245 lines; SHA-256 `48c092a77917adab1d4944ba3aa4b353b608645fb6c49ee1d949ca796cb2cca9`.

**Destination:** runtime/input/linux.

Replace handwritten protocol IO with portal-supported input/capture and tested compositor fallback; account for fragmentation, negotiation, cleanup and multiple outputs.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 14-16 | function/method | `log` | runtime/input/linux |
| 18-25 | function/method | `encode_wayland_string` | runtime/input/linux |
| 27-206 | class | `WaylandInput` | runtime/input/linux |
| 28-42 | function/method | `WaylandInput.__init__` | runtime/input/linux |
| 44-46 | function/method | `WaylandInput.get_socket_path` | runtime/input/linux |
| 48-52 | function/method | `WaylandInput.connect_to_wayland` | runtime/input/linux |
| 54-60 | function/method | `WaylandInput.send_message` | runtime/input/linux |
| 62-64 | function/method | `WaylandInput.send_registry_request` | runtime/input/linux |
| 66-68 | function/method | `WaylandInput.send_sync_request` | runtime/input/linux |
| 70-78 | function/method | `WaylandInput.receive_message` | runtime/input/linux |
| 80-117 | function/method | `WaylandInput.handle_events` | runtime/input/linux |
| 119-127 | function/method | `WaylandInput.create_virtual_pointer` | runtime/input/linux |
| 129-133 | function/method | `WaylandInput.send_motion_absolute` | runtime/input/linux |
| 135-140 | function/method | `WaylandInput.send_click` | runtime/input/linux |
| 142-166 | function/method | `WaylandInput.click` | runtime/input/linux |
| 168-206 | function/method | `WaylandInput.swipe` | runtime/input/linux |

## `tests/test_archive_extraction.py`

64 lines; SHA-256 `0d3a4d12f68f172932458f561cd9fbf9959f667eac06eaf0d52081b58911d616`.

**Destination:** Rust core/runtime tests + platform integration fixtures.

Port archive/corruption examples into native resource tests; add traversal/link/hash/atomic-install cases.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 17-60 | class | `TestArchiveExtraction` | Rust core/runtime tests + platform integration fixtures |
| 18-19 | function/method | `TestArchiveExtraction.setUp` | Rust core/runtime tests + platform integration fixtures |
| 21-22 | function/method | `TestArchiveExtraction.tearDown` | Rust core/runtime tests + platform integration fixtures |
| 24-35 | function/method | `TestArchiveExtraction.test_extract_zip_archive` | Rust core/runtime tests + platform integration fixtures |
| 37-51 | function/method | `TestArchiveExtraction.test_extract_tar_archive` | Rust core/runtime tests + platform integration fixtures |
| 53-60 | function/method | `TestArchiveExtraction.test_extract_corrupt_archive` | Rust core/runtime tests + platform integration fixtures |

## `tests/test_board_reader.py`

135 lines; SHA-256 `de661f5b7ec639c37c827937136c33786aceff348fd7162c8e885bbd637bd9dd`.

**Destination:** Rust core/runtime tests + platform integration fixtures.

Keep class mapping, king rejection, crop offsets, bounded no-board search and raw-promotion examples; add actual labeled model/image integration.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 21-111 | class | `TestFenExtraction` | Rust core/runtime tests + platform integration fixtures |
| 22-26 | function/method | `TestFenExtraction.setUp` | Rust core/runtime tests + platform integration fixtures |
| 28-37 | function/method | `TestFenExtraction.test_accepts_endgame_in_both_orientations` | Rust core/runtime tests + platform integration fixtures |
| 39-52 | function/method | `TestFenExtraction.test_rejects_missing_duplicate_kings_and_unknown_pieces` | Rust core/runtime tests + platform integration fixtures |
| 54-72 | function/method | `TestFenExtraction.test_board_read_retries_invalid_detections` | Rust core/runtime tests + platform integration fixtures |
| 64-64 | lambda | `TestFenExtraction.test_board_read_retries_invalid_detections.<lambda 1>` | Replace callback as part of Rust core/runtime tests + platform integration fixtures |
| 74-77 | function/method | `TestFenExtraction.test_successful_detection_skips_refined_search` | Rust core/runtime tests + platform integration fixtures |
| 79-85 | function/method | `TestFenExtraction.test_promotion_detection_can_read_raw_boxes` | Rust core/runtime tests + platform integration fixtures |
| 87-104 | function/method | `TestFenExtraction.test_refined_search_preserves_screen_coordinates` | Rust core/runtime tests + platform integration fixtures |
| 106-111 | function/method | `TestFenExtraction.test_failed_refined_search_returns_detection_error` | Rust core/runtime tests + platform integration fixtures |
| 114-131 | class | `TestBoardDetectionAndModelClasses` | Rust core/runtime tests + platform integration fixtures |
| 115-121 | function/method | `TestBoardDetectionAndModelClasses.test_model_constants` | Rust core/runtime tests + platform integration fixtures |
| 123-131 | function/method | `TestBoardDetectionAndModelClasses.test_onnx_session_lazily_loads` | Rust core/runtime tests + platform integration fixtures |

## `tests/test_downloader_and_cpu.py`

51 lines; SHA-256 `c8a396c708e561cd5cdac7ed1ec6d6759aaa2c708333c5e268156f2293038080`.

**Destination:** Rust core/runtime tests + platform integration fixtures.

Port selection/format examples; require ARM/x86 and instruction-negative cases; correct OS naming expectation.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 12-47 | class | `TestCpuFeaturesAndDownloader` | Rust core/runtime tests + platform integration fixtures |
| 13-15 | function/method | `TestCpuFeaturesAndDownloader.test_detect_os` | Rust core/runtime tests + platform integration fixtures |
| 17-21 | function/method | `TestCpuFeaturesAndDownloader.test_detect_cpu_info` | Rust core/runtime tests + platform integration fixtures |
| 23-27 | function/method | `TestCpuFeaturesAndDownloader.test_format_bytes` | Rust core/runtime tests + platform integration fixtures |
| 29-47 | function/method | `TestCpuFeaturesAndDownloader.test_choose_best_asset_windows_x86_64` | Rust core/runtime tests + platform integration fixtures |

## `tests/test_engine_service.py`

52 lines; SHA-256 `0758e5f364d49ad8ad0527eec85842bea8be5210f17239cd9f52653afd865828`.

**Destination:** Rust core/runtime tests + platform integration fixtures.

Keep opening/checkmate/handshake/cleanup tests; install the engine per target, remove Windows-only existence gate, add silent/hung/crashed-engine cases.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 12-48 | class | `TestEngineService` | Rust core/runtime tests + platform integration fixtures |
| 14-15 | function/method | `TestEngineService.setUpClass` | Rust core/runtime tests + platform integration fixtures |
| 17-19 | function/method | `TestEngineService.setUp` | Rust core/runtime tests + platform integration fixtures |
| 21-22 | function/method | `TestEngineService.tearDown` | Rust core/runtime tests + platform integration fixtures |
| 24-27 | function/method | `TestEngineService.test_engine_initialization_and_cleanup` | Rust core/runtime tests + platform integration fixtures |
| 29-36 | function/method | `TestEngineService.test_engine_best_move_standard_opening` | Rust core/runtime tests + platform integration fixtures |
| 38-43 | function/method | `TestEngineService.test_engine_checkmate_position` | Rust core/runtime tests + platform integration fixtures |
| 45-48 | function/method | `TestEngineService.test_get_config_file_path` | Rust core/runtime tests + platform integration fixtures |

## `tests/test_fen_and_notation.py`

59 lines; SHA-256 `ddfb250f88c0101ecd0bdb542207c16014a47b86bb56e9cc668b0149aeb98738`.

**Destination:** Rust core/runtime tests + platform integration fixtures.

Keep orientation/square/FEN/castling examples; replace tests treating invalid square input as a8 with explicit errors.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 13-55 | class | `TestFENAndNotation` | Rust core/runtime tests + platform integration fixtures |
| 14-17 | function/method | `TestFENAndNotation.test_notation_white` | Rust core/runtime tests + platform integration fixtures |
| 19-22 | function/method | `TestFENAndNotation.test_notation_black` | Rust core/runtime tests + platform integration fixtures |
| 24-27 | function/method | `TestFENAndNotation.test_notation_invalid` | Rust core/runtime tests + platform integration fixtures |
| 29-34 | function/method | `TestFENAndNotation.test_algebraic_to_index` | Rust core/runtime tests + platform integration fixtures |
| 36-42 | function/method | `TestFENAndNotation.test_fen_to_list` | Rust core/runtime tests + platform integration fixtures |
| 44-55 | function/method | `TestFENAndNotation.test_two_square_king_move` | Rust core/runtime tests + platform integration fixtures |

## `tests/test_move_validation.py`

52 lines; SHA-256 `bd2eb4c71bdc2e12b208eea3f210c9a8037615f4f6c1dd253a482e0e9bea138f`.

**Destination:** Rust core/runtime tests + platform integration fixtures.

Keep move/capture/en-passant/promotion/castling fixtures; add all underpromotions, black castling, unrelated changes and negative transitions.

| Lines | Kind | Symbol | Disposition / destination |
| --- | --- | --- | --- |
| 12-48 | class | `TestMoveValidation` | Rust core/runtime tests + platform integration fixtures |
| 13-16 | function/method | `TestMoveValidation.test_normal_pawn_move` | Rust core/runtime tests + platform integration fixtures |
| 18-21 | function/method | `TestMoveValidation.test_piece_move` | Rust core/runtime tests + platform integration fixtures |
| 23-26 | function/method | `TestMoveValidation.test_en_passant` | Rust core/runtime tests + platform integration fixtures |
| 28-31 | function/method | `TestMoveValidation.test_promotion_move` | Rust core/runtime tests + platform integration fixtures |
| 33-39 | function/method | `TestMoveValidation.test_castling_moves` | Rust core/runtime tests + platform integration fixtures |
| 41-48 | function/method | `TestMoveValidation.test_promotion_helpers` | Rust core/runtime tests + platform integration fixtures |

## Build, configuration and documentation files

| File | Lines | SHA-256 | Disposition |
| --- | --- | --- | --- |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | 100 | `7e763100397485a6bcf6ebb3d55c6aeb459a318704c91bd952980caea7a0da2f` | Extend OS/install/permissions/capture/ABI diagnostics for Android; correct stale shortcut/version references during release docs update. |
| `.github/ISSUE_TEMPLATE/config.yml` | 5 | `6d33c350a4501873f46e91425078bedacba3d5e5e0ddcb8fb34f708cd8b15d3d` | Keep support links, update paths only if documentation moves. |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | 35 | `74c8d27cff8da7ab5058777cfd1d790e9e9e5e6da75607fbb00fabdf783477e2` | Keep request structure; no runtime migration. |
| `.github/PULL_REQUEST_TEMPLATE.md` | 27 | `366748799d45a251cec30a3c1838806e4c2342ddf01d572703dea96da331617c` | Replace hard-coded 25-test claim with target-specific required checks when new checks exist. |
| `.github/workflows/ci.yml` | 69 | `f8d73b00e7ec1d677d35781ada63b9a8744cb5cff491d574f55fa8f0e1f6b7e4` | Retain legacy jobs; add non-skipping native model/engine tests and platform artifact jobs before cutover. |
| `.gitignore` | 89 | `66c6ad61594679848af9805ba910b89e28ae3afd5cb2033f17cd8695581611a2` | Add new generated Flutter/Cargo/NDK output rules only when those directories exist; keep fixtures and lockfiles trackable. |
| `CONTRIBUTING.md` | 92 | `dff7e3e0769cadc28ac7d1e2ebe95edf5250cdc58ba86a3fa041ebdf431084da` | Add native/Flutter/platform test instructions once implemented; retain offline and explicit error-handling intent. |
| `LICENSE` | 11 | `42af0cdc9b12a349f3ea1e4b9b3ef553422fbefcb7711f5398220b891c91f114` | Preserve repository notice; verify full license text and separately resolve exact engine/model/dependency redistribution obligations. |
| `README.md` | 265 | `8eeef89f5b43d46637736426e4e65ff5f7395836ba095cadef14ce5c06a02c5b` | Retain current release instructions during migration; add Android/desktop matrix and accurate offline setup after implementation. |
| `SHORTCUTS.md` | 25 | `80d950f4db0d41fae0e4a992444bcc3a244fdfd113fdbf9516a9642772d9af3d` | Preserve mode-sensitive desktop actions; provide touch alternatives on Android. |
| `engine_config.txt` | 11 | `995eedc2b801addebb5f0bf814494d9e6b8f64c17cda24a5db8aeb98fd5ee896` | Import supported engine settings explicitly; use mobile-aware memory/thread limits and preserve original user file. |
| `linux.spec` | 57 | `7be3d5a6e411a5e9d89f83bc6e62feab7d1d8a55926a6ffc7eb6ecf3819db938` | Keep Python v2.3.1 release; later replace with tested Flutter Linux distribution and portal/native dependency packaging. |
| `requirements.txt` | 10 | `84caa38bb167ba773a4a5c26ef72c00045a8a7104e46860df65fd065947a38b6` | Legacy Python environment only; new builds use pinned Cargo/Flutter/NDK/native-engine/runtime dependencies. |
| `win.spec` | 57 | `7ed2e9a9967e800e1866e804234912058e11a910ed21441483b01a71012aa46a` | Keep Python v2.3.1 release; later replace with Flutter Windows packaging and native resource/engine artifacts. |

## Assets and exclusions

The four tracked `assets/` media/icon files are reusable branding/demo inputs, not source to translate. Their distribution terms should be recorded with the new package. The local ignored ONNX model and Stockfish executable were used for baseline integration; their hashes are in the plan. They were not decompiled or retrained. Virtual environment contents, build/dist outputs, caches and Git internals are excluded from authored-source review.

The ignored local `release_notes.md` describes v2.3.0 and was inspected as historical documentation; it is not a committed release artifact. The earlier user-provided `image.png` is absent from this snapshot and must be restored/approved as a fixture before making it a permanent zoom regression test.

No production modules, exports, configuration, tests or release specs were changed to prepare these planning documents.
