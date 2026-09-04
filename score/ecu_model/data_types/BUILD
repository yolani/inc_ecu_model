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
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "data_types",
    srcs = [
        "array.py",
        "common.py",
        "composite.py",
        "cpp.py",
        "enum.py",
        "franca.py",
        "primitives.py",
        "protobuf.py",
        "struct.py",
        "union.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//score/ecu_model",
        "@score_ecu_model_pip//pydantic",
    ],
)
