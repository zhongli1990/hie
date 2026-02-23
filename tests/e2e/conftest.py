"""
OpenLI HIE E2E Test Configuration

Provides shared constants and fixtures for all E2E test suites.
The expected platform version is read from the HIE_VERSION env var
(injected by run_e2e_tests.sh from the VERSION file).
"""

import os

# Single source of truth for version assertions across all E2E test suites.
# Injected by scripts/run_e2e_tests.sh from the root VERSION file.
EXPECTED_VERSION = os.environ.get("HIE_VERSION", "1.9.7")
