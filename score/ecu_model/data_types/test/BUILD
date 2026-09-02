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

load("@rules_python//python:defs.bzl", "py_test")

py_test(
    name = "primitives_test",
    size = "small",
    srcs = ["primitives_test.py"],
    deps = [
        "//score/ecu_model/data_types",
    ],
)

py_test(
    name = "common_test",
    size = "small",
    srcs = ["common_test.py"],
    deps = [
        "//score/ecu_model/data_types",
        "@score_ecu_model_pip//pydantic",
    ],
)

py_test(
    name = "franca_test",
    size = "small",
    srcs = ["franca_test.py"],
    deps = [
        "//score/ecu_model/data_types",
        "@score_ecu_model_pip//pydantic",
    ],
)

py_test(
    name = "cpp_test",
    size = "small",
    srcs = ["cpp_test.py"],
    deps = [
        "//score/ecu_model/data_types",
        "@score_ecu_model_pip//pydantic",
    ],
)

py_test(
    name = "protobuf_test",
    size = "small",
    srcs = ["protobuf_test.py"],
    deps = [
        "//score/ecu_model/data_types",
        "@score_ecu_model_pip//pydantic",
    ],
)
