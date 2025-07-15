## Updates made by Gemini

### 1. `update.py`

*   **Argument Parsing**:
    *   Added new command-line arguments for granular control:
        *   `--companies-unindexed`: To specifically run the unindexed companies update.
        *   `--update-weekly-planning`: To specifically update weekly planning application files.
        *   `--update-annual-planning`: To specifically update annual planning application files.
        *   `--generate-postcode-boundaries`: To specifically generate postcode boundaries from OpenStreetMap data.
*   **Execution Logic**:
    *   The `run_all` and `interactive` flags are now determined based on whether *any* argument (including the new granular ones) is provided. If no arguments are given, `run_all` is `True` and `interactive` is `True`. Otherwise, both are `False`.
    *   The execution flow for each module (`companies`, `planning_applications`, `openstreetmap`) now prioritizes the new granular arguments. If a specific granular argument is present, only that specific task is executed for that module, bypassing the general module update.
    *   The `interactive` flag is consistently passed down to the main functions of each module.
    *   New `run_unindexed_only`, `run_weekly_only`, `run_annual_only`, and `run_postcode_boundaries_only` flags are passed to the respective module functions to control their internal behavior.

### 2. `src/companies.py`

*   **Function Signature**:
    *   The `companies()` function now accepts `interactive=True` and a new `run_unindexed_only=False` boolean parameter.
    *   The `companies_unindexed()` and `load_data()` functions also accept the `interactive` parameter.
*   **Conditional Execution**:
    *   If `run_unindexed_only` is `True` (meaning `--companies-unindexed` was passed to `update.py`), `companies()` will *only* call `companies_unindexed()` and then return, skipping the general company update process.
    *   The `companies_unindexed()` function's prompt for batch size is now conditional on `interactive`. In non-interactive mode, it will proceed without prompting.
*   **Interactive Prompts**:
    *   User input prompts (`input()`) within `load_data()` are now conditional on the `interactive` flag. In non-interactive mode, default actions (e.g., downloading the latest data) are taken.

### 3. `src/land_transactions.py`

*   **Function Signature**:
    *   The `land_transactions()` and `load_data()` functions now accept an `interactive=True` boolean parameter.
*   **File Update Logic**:
    *   The logic for downloading the land transactions file within `load_data()` has been refined. It now correctly handles both interactive (prompting the user and respecting their 'y/N' input) and non-interactive (always attempting to update/download) modes, while consistently checking for the file's existence.

### 4. `src/planning_applications.py`

*   **Function Signature**:
    *   The `planning_applications()` function now accepts `interactive=True`, `run_weekly_only=False`, and `run_annual_only=False` boolean parameters.
    *   The `load_data()`, `update_weekly_files()`, and `update_annual_files()` functions now accept the `interactive` parameter.
*   **Refactored Update Flow**:
    *   The `load_data()` function no longer contains the logic for *downloading* weekly or annual files; it now solely focuses on *loading* existing data.
    *   The `planning_applications()` function now contains the primary logic for deciding whether to call `update_weekly_files()` or `update_annual_files()`, based on the `interactive` flag and the new `run_weekly_only`/`run_annual_only` flags.
    *   If `run_weekly_only` or `run_annual_only` is `True`, only the corresponding update is performed.
    *   If neither specific flag is set, the general update logic (which includes conditional prompts for weekly/annual updates based on `interactive`) is executed.

### 5. `src/openstreetmap.py`

*   **Function Signature**:
    *   The `openstreetmap()` function now accepts `interactive=True` and a new `run_postcode_boundaries_only=False` boolean parameter.
    *   The `load_data()`, `generate_postcode_boundaries()`, and `print_datasets_markdown()` functions now accept the `interactive` parameter.
*   **Conditional Execution**:
    *   If `run_postcode_boundaries_only` is `True` (meaning `--generate-postcode-boundaries` was passed to `update.py`), `openstreetmap()` will *only* call `generate_postcode_boundaries()` (after loading necessary data) and then return.
*   **Interactive Prompts**:
    *   User input prompts (`input()`) within `load_data()`, `generate_postcode_boundaries()`, and `print_datasets_markdown()` are now conditional on the `interactive` flag. In non-interactive mode, default actions (e.g., downloading data, regenerating postcodes/markdown) are taken.

### 6. `src/global_ml_building_footprints.py`

*   **Function Signature**:
    *   The `global_ml_building_footprints()` function already accepted an `interactive=True` boolean parameter from previous steps.
*   **Interactive Prompts**:
    *   The user input prompt (`input()`) is conditional on the `interactive` flag. In non-interactive mode, the default action (downloading updated data) is taken.

## TODO

1. don't assume subsections should run if parent section is run, e.g. if `--openstreetmap` is run, it shouldn't automatically generate postcode boundaries or output the markdown text. Likely the same in other sections, e.g. running `--companies` shouldn't assume we also want to run `-companies-unindexed`. Subsections should be runnable on their own (e.g. `--generate-postcode-boundaries` should be able to run without `--openstreetmap`)
2. add [timestamps] to console outputs (abstract this into a separate function that can be reused and updated with ease)