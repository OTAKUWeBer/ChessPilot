## Description

Please include a summary of the change, the rationale behind it, and which issue (if any) it resolves.

Fixes #(issue)

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] ♻️ Code refactoring / Cleanup (improving structure without changing behavior)
- [ ] 📝 Documentation update
- [ ] 🧪 Tests (adding or fixing tests)
- [ ] 📦 Build / Packaging / Spec update

## Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my code
- [ ] I have commented my code in hard-to-understand areas
- [ ] No bare `except: pass` blocks were introduced (CodeFactor compliance)
- [ ] All 25 automated tests pass locally: `python -m unittest discover tests -v`
- [ ] Offline operation is preserved (no network requests during the game loop)
- [ ] Windows input and Linux Wayland input behavior remain functional
- [ ] I have tested these changes on:
  - [ ] Windows
  - [ ] Linux (X11 / Wayland)
