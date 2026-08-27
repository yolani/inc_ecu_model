# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

"""Ruff aspects."""

load("@aspect_rules_lint//lint:ruff.bzl", "lint_ruff_aspect")
load("@bazel_skylib//rules:write_file.bzl", "write_file")

visibility(["//..."])

# Define the ruff linter aspect for Python targets. The repo's //:.ruff.toml
# is passed so the lint aspect and `ruff format` read the same config file,
# but that file currently has no [lint]/[lint.*] tables, so ruff still falls
# back to its own built-in default rule selection
# (https://docs.astral.sh/ruff/rules/#default-rules). Wiring the file in now
# means a future project-specific lint override only requires adding a
# [lint] table to //:.ruff.toml, not touching this aspect definition.
ruff = lint_ruff_aspect(
    binary = Label("@aspect_rules_lint//lint:ruff_bin"),
    configs = [Label("//:.ruff.toml")],
)

def make_script(name, content):
    write_file(
        name = name + "_script",
        out = name.replace("-", "_") + ".sh",
        is_executable = True,
        content = ["#!/usr/bin/env bash", "set -euo pipefail", 'TARGETS="${*:-//...}"', 'cd "${BUILD_WORKSPACE_DIRECTORY}"'] + content,
    )

def use_ruff_targets(fix_name = "ruff.fix", check_name = "ruff.check"):
    """Declare ruff check and fix script targets.

    Unlike clang-tidy/pylint, `aspect_rules_lint`'s ruff integration can apply
    fixes directly (via `ruff check --fix`) instead of emitting a patch file,
    so `ruff.fix` runs bazel with `--config=ruff-fix` and is done.
    """
    make_script(fix_name, [
        'echo "=== ruff autofix: ${TARGETS} ==="',
        "bazel test --config=ruff-fix ${TARGETS}",
    ])

    make_script(check_name, [
        'echo "=== ruff check: ${TARGETS} ==="',
        "bazel test --config=ruff ${TARGETS}",
    ])
