## v0.3.0 (2026-07-29)

### Feat

- non-assignment interactions (`?[...]` without `%{{var}}`) now support the full shape set: multi-select (`?[A||B]`), text input (`?[...question]`), and buttons with text (`?[A|B|...question]`); parse results carry `question` and `is_multi_select`
- `process()` normalizes non-assignment answers (button display -> value, free text passed through) and returns them in `metadata["answer"]`; input values are merged from any user_input key (canonical key: `input`, exported as `DEFAULT_NON_ASSIGNMENT_INPUT_KEY`)
- context messages accept a `user_answer` extension field (exported as `USER_ANSWER_CONTEXT_KEY`) so the answer to a no-variable interaction reaches the next LLM request; empty answer skips the turn, absent field keeps the legacy `{user: "ok"}` behavior
- next-interaction preview distinguishes single/multi select and text input for non-assignment blocks

### Fix

- target variable is now derived from the parsed interaction instead of text interpolation variables (`?[{{userName}} Continue]` no longer targets `userName`)
- context messages are sanitized to `{role, content}` before reaching the LLM

### Refactor

- remove the dead legacy `markdown_flow.utils` module (unreferenced duplicate of `parser/`)

## v0.2.4 (2025-09-18)

### Feat

- add multi-select interaction support with `||` separator syntax
- implement BUTTONS_MULTI_SELECT and BUTTONS_MULTI_WITH_TEXT interaction types
- add intelligent separator detection with fault tolerance
- enhance variable system to support list[str] values alongside str values

### BREAKING CHANGE

- user_input parameter type changed from `str` to `dict[str, list[str]]`
- variables parameter now supports `dict[str, str | list[str]]` for multi-select values
- UserInput.content field changed from `str` to `dict[str, list[str]]`

## v0.3.0 (2025-09-03)

### Fix

- restore workflow configuration and resolve rebase conflicts (#18)

## v0.2.0 (2025-09-03)

### Feat

- configure project release automation (#17)

## v0.1.5 (2025-09-03)

### Feat

- update pyproject (#16)
- update commitizen config for auto release (#15)
- udpate cz conf to auto release
- add automated release workflow with version management (#11)
- add markdownlint integration for consistent documentation quality (#10)
- add markdownlint integration for consistent documentation quality (#10)
- add editorconfig focused on Python backend development (#8)
- add commitizen configuration for automated version management (#6)
- interactive syntax escape (#3)

### Fix

- variable parsing processing in interaction (#2)
