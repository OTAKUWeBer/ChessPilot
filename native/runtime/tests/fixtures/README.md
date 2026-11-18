# Regression fixtures

The JSON data records fixed promotion geometry, download selection and wlroots protocol expectations, including source hashes and provenance. These fixtures were captured from the original implementation and remain useful independent of it. No legacy runtime or source is required to run the tests.

- `promotion.json`: both colors, fractional board sizes, confidence boundaries and menu ordering.
- `downloads.json`: CPU compatibility, architecture rejection and safe baseline selection.
- `wayland.json`: pointer messages and gesture timing; the runtime also checks framing, callbacks, cancellation and resource cleanup.

Vision preprocessing/model fixtures and their licenses/provenance are described in [vision/README.md](vision/README.md). Keep the provenance fields when updating data; do not replace actual regression coverage with labels or timing assumptions.
