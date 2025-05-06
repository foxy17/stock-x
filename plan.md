# Refactoring Plan: NSE Announcements Tracker

This plan outlines the steps to refactor the NSE Announcements Tracker application for better modularity, maintainability, and adherence to best practices like SOLID and DRY, with considerations for packaging into a standalone executable.

## Phase 1: Setup and Configuration

- [ ] Create `requirements.txt` with all necessary dependencies (`PyQt5`, `requests`, `beautifulsoup4`, `lxml`, `playwright`, `playwright-stealth`).
- [ ] Create `config.py` to store constants.
  - [ ] **Packaging Consideration:** Define `STORAGE_FILE_PATH` in `config.py`. Ensure the logic to determine its *actual runtime path* (considering packaged vs. script mode) is handled appropriately, likely within `storage.py`. (See Phase 2 - `storage.py`).
  - [ ] Move `MAX_STORED_IDENTIFIERS` to `config.py`.
  - [ ] Move default URL (`https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml`) from `task.py` to `config.py`.
  - [ ] Move polling interval (`5000` ms) from `task.py` to `config.py`.
  - [ ] Move highlight duration (`300` seconds) from `task.py` to `config.py`.
  - [ ] Move new item highlight color (`QColor(...)`) from `task.py` to `config.py`.
- [ ] Update existing files (`tracking.py`, `task.py`) to import relevant constants from `config.py` instead of defining them locally.

## Phase 2: Decompose `tracking.py`

- [ ] Create `fetcher.py`.
  - [ ] Move the `fetch_content` function from `tracking.py` to `fetcher.py`.
  - [ ] Ensure necessary imports (`playwright`, `logging`, etc.) are moved or added to `fetcher.py`.
  - [ ] Update `fetch_content` to potentially accept browser arguments/options from `config.py`.
- [ ] Create `parser.py`.
  - [ ] Create a new function (e.g., `parse_xml_items`) in `parser.py`.
  - [ ] Move the `BeautifulSoup` XML parsing logic from `get_new_items` (in `tracking.py`) into `parse_xml_items`. This function should take raw XML content string as input and return a list of item dictionaries (or None/empty list on error).
  - [ ] Ensure necessary imports (`BeautifulSoup`, `logging`, `hashlib`) are moved or added to `parser.py`.
- [ ] Create `storage.py`.
  - [ ] **Packaging Consideration:** Implement logic in `storage.py` to determine the correct path for the `STORAGE_FILE_PATH` (imported from `config.py`) at runtime. This should handle both running as a script and running as a packaged executable (e.g., using `sys.executable` or `sys._MEIPASS` if applicable, or placing it in user data directories).
  - [ ] Move `load_seen_items` and `save_seen_items` functions from `tracking.py` to `storage.py`, ensuring they use the dynamically determined storage path.
  - [ ] Move the global state (`seen_item_objects_list`, `seen_item_identifiers_set`) management into `storage.py`. Consider encapsulating this state within a class (e.g., `SeenItemsStore`) or keeping them as module-level variables initialized by `load_seen_items`.
  - [ ] Add functions like `get_all_items` and `has_seen_identifier` to `storage.py` to provide a clean interface.
  - [ ] Ensure necessary imports (`json`, `os`, `logging`, `config`, `sys`) are present in `storage.py`.
- [ ] Refactor `tracking.py` (or rename to `data_manager.py`).
  - [ ] Remove the moved functions and state (`fetch_content`, parsing logic, `load_seen_items`, `save_seen_items`, global lists/sets).
  - [ ] Update `get_new_items`:
    - Import and call `fetch_content` from `fetcher.py`.
    - Import and call `parse_xml_items` from `parser.py`.
    - Import and use the `storage.py` module/class to check if an item identifier has been seen (`has_seen_identifier`).
    - If an item is new, add it to the storage using a function like `storage.add_item()`.
    - Return the list of *newly added* item dictionaries.
  - [ ] Update `get_initial_items`:
    - Import and call the appropriate function from `storage.py` (e.g., `get_all_items`) to load items at startup.
  - [ ] Ensure imports from the new modules (`fetcher`, `parser`, `storage`) are added.

## Phase 3: Update `task.py` (UI Layer)

- [ ] Update imports at the top of `task.py` to reflect the changes (e.g., import `get_new_items`, `get_initial_items` from the refactored `tracking.py` or `data_manager.py`).
- [ ] Ensure `task.py` imports and uses constants from `config.py` (URL, poll interval, colors, etc.).
- [ ] Verify that `load_initial_items` and `poll_data` functions correctly interact with the updated data layer functions.
- [ ] Verify that item data structure (dictionaries) passed to `add_item_to_list` remains consistent.

## Phase 4: Testing and Verification (Script Mode)

- [ ] Run the application as a Python script (`python task.py`).
- [ ] Verify initial items are loaded correctly from the storage file (check its location based on the new logic in `storage.py`).
- [ ] Verify polling starts and fetches new data.
- [ ] Verify new items are correctly identified, displayed, and highlighted.
- [ ] Verify clicking items still prompts to open links correctly.
- [ ] Verify items are saved correctly on exit/stop and loaded on next start.
- [ ] Check logs for any new errors or warnings.

## Phase 5: Controller Logic Separation

- [ ] Create `controller.py` (or `app_logic.py`).
- [ ] Define a class (e.g., `AppController`) to manage application state and logic.
- [ ] Move polling timer setup and `poll_data` logic from `MainWindow` to the `AppController`.
- [ ] Move state variables (`polling`, `target_url`) from `MainWindow` to `AppController`.
- [ ] Implement mechanisms for the `AppController` to communicate back to the `MainWindow` (e.g., using signals/slots or callbacks) to update the UI (status label, list widget).
- [ ] Instantiate the `AppController` in `MainWindow` or `if __name__ == "__main__":` block and connect UI actions (start/stop buttons) to controller methods.

## Phase 6: Packaging with `auto-py-to-exe` / PyInstaller

- [ ] **Playwright Browsers:** Decide on strategy:
    - Option A: Instruct users of the `.exe` to run `playwright install` manually post-installation. (Simpler packaging, requires extra user step).
    - Option B: Attempt to bundle browsers using PyInstaller hooks or `--add-data` options. (More complex setup, potentially larger `.exe`, self-contained). Document the chosen approach.
- [ ] **Prepare for Packaging:**
    - Ensure `requirements.txt` is up-to-date.
    - Install `pyinstaller` (usually handled by `auto-py-to-exe`).
- [ ] **Use `auto-py-to-exe`:**
    - Select `task.py` (or the main script after controller refactoring) as the script entry point.
    - Choose "One File" or "One Directory" mode. "One Directory" is often easier for debugging initially.
    - Choose "Window Based (hide console)" for the GUI application.
    - **Crucially:** Use the "Additional Files" section if needed (e.g., potentially for browser binaries if using Option B, or other data files). The logic in `storage.py` should aim to find `seen_items_store.json` relative to the executable, so it doesn't need explicit bundling *if* saved next to the exe.
    - Add necessary hidden imports if PyInstaller misses them (common ones for PyQt5 include `PyQt5.sip`, specific plugins like `PyQt5.QtNetwork`). Check PyInstaller output/logs.
- [ ] **Build the Executable.**
- [ ] Locate the executable in the `output` directory.

## Phase 7: Testing and Verification (Executable Mode)

- [ ] Run the generated `.exe` file *outside* the development environment/folders.
- [ ] If using Playwright Option A, ensure browsers are installed (`playwright install`).
- [ ] Verify the application starts correctly.
- [ ] Check the expected location for `seen_items_store.json` (e.g., next to the `.exe` or in user data folder) and verify it's created/updated.
- [ ] Verify initial items load (if the store file existed).
- [ ] Verify polling works and new items are fetched and displayed.
- [ ] Verify link opening works.
- [ ] Test on a different machine (if possible) that doesn't have Python or the project dependencies installed. 