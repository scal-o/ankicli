# ankicli

## Description

`ankicli` is (or will be) a command line tool for managing Anki cards from markdown files. It uses the Anki Connect API to create, update, and upload notes and media to Anki decks.

## Installation
If you are willing to try `ankicli`, you can install it via cloning the git repository and installing the dependencies via `uv sync`. 
If you are using `uv`, the package should then be installed automatically as a local (editable) package.


## Usage
The actual _cli_ part of `ankicli` is not yet implemented. However, you can use the library directly in Python scripts or in an interactive Python session. 
An example usage can be found in the example.py file in the root directory. This example expects to find markdown files in the `vault/` directory and will process them to create Anki notes.

## Dependencies
External dependencies are managed via `pyproject.toml` and include:

-   mistune
-   numpy
-   pandas
-   pyyaml
-   requests


Dev dependencies (test deps) include:

-   pytest
-   pytest-cov
-   pytest-mock
-   requests-mock

I'm aiming to keep the dependencies minimal and have a good test coverage for edge cases etc. 
To check the test coverage, run `uv run pytest --cov` or similar.

## Project Structure
- ankicli/: Main application code
    - anki_api/: Modules for interacting with the Anki Connect API.
    - config/: Configuration files.
    - modelModule.py: Handle Anki note models.
    - noteModule.py: Handle note creation and management.
    - parseModule.py: Handle parsing markdown files.
    - renderer/: Modules for rendering content (e.g., images, math).
    - re_exprs.py: Regular expressions.
- tests/: Test suite
- vault/: Contains markdown files to be processed.
- pyproject.toml: Project metadata and dependencies.
- README.md: This file.
