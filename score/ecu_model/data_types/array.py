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

from pydantic import Field, ValidationInfo, field_validator, model_validator

from score.ecu_model.data_types.common import DataTypeBase, DataTypeKind, TypeRef


class ArrayDataType(DataTypeBase):
    """Definition of an array data type with element type and optional dimensions."""

    kind: Literal[DataTypeKind.ARRAY] = Field(default=DataTypeKind.ARRAY, frozen=True)
    identifier: str | None = Field(
        default=None,
        description="Identifier of a named array definition in its source namespace; absent for inline arrays",
    )
    data_type: TypeRef = Field(
        description="Array element type definition",
    )
    is_inline: bool = Field(
        default=False,
        description="Whether the array is declared inline without a type name",
    )
    dimension_min: int | None = Field(
        default=None,
        description="Minimum dimension bound",
    )
    dimension_max: int | None = Field(
        default=None,
        description="Maximum dimension bound",
    )

    @field_validator("identifier")
    @classmethod
    def _validate_optional_name(cls, value: str | None, info: ValidationInfo) -> str | None:
        """
        Validate identifier using parent validator when provided.
        Overwrites the parent class's _validate_name method to allow None for inline arrays.
        """
        if value is None:
            return value
        return cls._validate_name(value, info)

    @field_validator("dimension_min", "dimension_max")
    @classmethod
    def _validate_dimension_bound_is_non_negative(cls, value: int | None) -> int | None:
        """Validate array dimension bounds as non-negative integers when provided."""
        if value is not None and value < 0:
            raise ValueError("array dimension bounds must be non-negative")
        return value

    @model_validator(mode="after")
    def _validate_array_constraints(self) -> ArrayDataType:
        """Validate array naming and dimension constraints."""
        if self.is_inline and self.identifier is not None:
            raise ValueError("inline arrays must not have an identifier")
        if self.is_inline and self.namespace is not None:
            raise ValueError("inline arrays must not have a namespace")
        if not self.is_inline and self.identifier is None:
            raise ValueError("non-inline arrays require an identifier")
        if (
            self.dimension_min is not None
            and self.dimension_max is not None
            and self.dimension_min > self.dimension_max
        ):
            raise ValueError("dimension_min must not be greater than dimension_max")
        return self
