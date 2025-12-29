# datasette-turnstile

[![PyPI](https://img.shields.io/pypi/v/datasette-turnstile.svg)](https://pypi.org/project/datasette-turnstile/)
[![Changelog](https://img.shields.io/github/v/release/simonw/datasette-turnstile?include_prereleases&label=changelog)](https://github.com/simonw/datasette-turnstile/releases)
[![Tests](https://github.com/simonw/datasette-turnstile/actions/workflows/test.yml/badge.svg)](https://github.com/simonw/datasette-turnstile/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/datasette-turnstile/blob/main/LICENSE)

Integrate CAPTCHAs powered by Cloudflare Turnstile

## Installation

Install this plugin in the same environment as Datasette.
```bash
datasette install datasette-turnstile
```
## Usage

Usage instructions go here.

## Development

To set up this plugin locally, first checkout the code. You can confirm it is available like this:
```bash
cd datasette-turnstile
# Confirm the plugin is visible
uv run datasette plugins
```
To run the tests:
```bash
uv run pytest
```
