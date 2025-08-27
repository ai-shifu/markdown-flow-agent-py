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
