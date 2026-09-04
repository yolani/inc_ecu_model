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
from __future__ import annotations

from typing import Literal

from pydantic import Field, FilePath

from score.ecu_model.data_types.common import DataTypeBase, DataTypeKind, DataTypeSource


class ExternalDataType(DataTypeBase):
    """Definition of a type provided by an existing C++ header without modeled internals."""

    kind: Literal[DataTypeKind.EXTERNAL] = Field(default=DataTypeKind.EXTERNAL, frozen=True)
    source_kind: DataTypeSource = Field(
        default=DataTypeSource.CPP_HEADER_FILE,
        description="Origin of the data type definition, defaults to CPP_HEADER_FILE for external types",
    )
    # TODO: could be Path?
    header: FilePath = Field(
        description="Header include path or explicitly quoted/bracketed include",
    )
