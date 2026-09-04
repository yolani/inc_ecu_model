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

from pydantic import ConfigDict, Field, field_validator
from typing import Literal

from score.ecu_model.data_types.common import (
    DataTypeBase,
    DataTypeKind,
    DataTypeRef,
    DataTypeSource,
    ValidationInfo,
)
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.model import ModelElement, ModelRef, ModelRegistry


class EnumValue(ModelElement):
    """A named enum literal with an optional numeric value."""

    model_config = ConfigDict(frozen=True)

    identifier: str = Field(
        description="Identifier of the enum literal in its source namespace",
    )
    value: int | None = Field(
        default=None,
        description="Optional numeric value assigned to the enum literal",
    )

    @field_validator("value", mode="before")
    @classmethod
    def _reject_boolean_values(cls, value: int | bool | None) -> int | None:
        """Reject booleans so they are not silently converted to 1 or 0."""
        if isinstance(value, bool):
            raise ValueError("enum value must be an integer, not boolean")
        return value

    @field_validator("value", mode="before")
    @classmethod
    def _reject_negative_values(cls, value: int | bool | None) -> int | None:
        """Reject negative values for the enum."""
        if value is not None and value < 0:
            raise ValueError("enum value must be non-negative")
        return value


class EnumDataType(DataTypeBase):
    """A declared enum data type with named literals."""

    kind: Literal[DataTypeKind.ENUM] = Field(default=DataTypeKind.ENUM, frozen=True)
    extends: DataTypeRef | None = Field(
        default=None,
        description="Optional enum definition extended by this enum",
    )
    underlying_type: PrimitiveDataType = Field(
        default=PrimitiveDataType.UINT32,
        description="Primitive type used for enum storage",
    )
    values: tuple[ModelRef, ...] = Field(
        default_factory=tuple,
        description="References to named enum literals, not changeable after creation",
    )

    @field_validator("values")
    @classmethod
    def _validate_value_identifiers(cls, values: tuple[ModelRef, ...], info: ValidationInfo) -> tuple[ModelRef, ...]:
        """Validate enum literals according to their enclosing source language."""
        source_kind = info.data.get("source_kind")
        if source_kind is None:
            return values
        identifier_pattern, _, _ = cls._get_language_spec(source_kind)
        for value_ref in values:
            enum_value = value_ref.resolve()
            if not isinstance(enum_value, EnumValue):
                raise TypeError(
                    f"Reference {value_ref.target_id} points to {type(enum_value).__name__}, expected EnumValue"
                )
            if not identifier_pattern.match(enum_value.identifier):
                kind_name = getattr(source_kind, "name", str(source_kind))
                raise ValueError(
                    f"Invalid {kind_name} enum value identifier '{enum_value.identifier}': "
                    "must start with a letter or underscore, followed by letters, digits or underscores"
                )
        return values

    @field_validator("values")
    @classmethod
    def _validate_value_definitions(cls, values: tuple[ModelRef, ...]) -> tuple[ModelRef, ...]:
        """Validate enum literal value definitions and uniqueness."""
        enum_values = tuple(value_ref.resolve() for value_ref in values)
        has_explicit_values = any(enum_value.value is not None for enum_value in enum_values)
        has_implicit_values = any(enum_value.value is None for enum_value in enum_values)
        if has_explicit_values and has_implicit_values:
            raise ValueError("enum values must either all be explicitly defined or all be omitted")
        identifiers = [enum_value.identifier for enum_value in enum_values]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("enum value identifiers must be unique")
        explicit_values = [enum_value.value for enum_value in enum_values if enum_value.value is not None]
        if len(explicit_values) != len(set(explicit_values)):
            raise ValueError("explicit enum values must be unique")
        return values

    @field_validator("extends")
    @classmethod
    def _validate_inheritance(cls, extends: DataTypeRef | None, info: ValidationInfo) -> DataTypeRef | None:
        """Validate the enum inheritance according to their enclosing source language and kind."""
        if extends is not None:
            source_kind = info.data.get("source_kind")
            if source_kind != DataTypeSource.FRANCA:
                raise ValueError(f"Enum inheritance is only allowed for FRANCA source kind, but got {source_kind}")
            if extends.target_id in ModelRegistry.elements:
                base_type = extends.resolve()
                if base_type.kind != DataTypeKind.ENUM:
                    raise ValueError(
                        f"EnumDataType can only extend another enum data type, "
                        f"but referenced base type '{extends.target_id}' is of kind '{base_type.kind}'"
                    )
        return extends
