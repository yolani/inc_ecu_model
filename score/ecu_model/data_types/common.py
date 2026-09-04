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

from enum import Enum
import re
from typing import Any

from pydantic import Field, FilePath, ValidationInfo, field_validator

from score.ecu_model.data_types.cpp import CPP_IDENTIFIER_PATTERN, CPP_NAMESPACE_PATTERN, CPP_SEPARATOR
from score.ecu_model.data_types.franca import FRANCA_IDENTIFIER_PATTERN, FRANCA_PACKAGE_PATTERN, FRANCA_SEPARATOR
from score.ecu_model.data_types.primitives import PrimitiveType
from score.ecu_model.data_types.protobuf import (
    PROTOBUF_IDENTIFIER_PATTERN,
    PROTOBUF_PACKAGE_PATTERN,
    PROTOBUF_SEPARATOR,
)
from score.ecu_model.ecu_model import EcuModelElement, EcuModelRef


class DataTypeKind(str, Enum):
    """
    Discriminator values for concrete DataTypeBase models.
    Used to distinguish between different kinds of data types in the model when (de-)serializing them.
    Primitives are intentionally absent: they are builtin and therefore never declared.
    """

    ENUM = "enum"
    STRUCT = "struct"
    UNION = "union"
    ARRAY = "array"
    MAP = "map"
    TYPEDEF = "typedef"
    EXTERNAL = "external"  # TODO: do we need this or can this be deducted from the source_kind property?

    def __str__(self) -> str:
        """Return the canonical data type kind name."""
        return self.value


class DataTypeSource(str, Enum):
    """
    IDL (Interface Definition Language) from which the data type originates.
    """

    FRANCA = "franca"
    PROTOBUF = "protobuf"
    CPP_HEADER_FILE = "cpp_header_file"

    def __str__(self) -> str:
        """Return the canonical data type source name."""
        return self.value


class DataTypeBase(EcuModelElement):
    """Shared metadata for data types that are declared in a source language."""

    kind: DataTypeKind = Field(
        description="Discriminator identifying the concrete data type definition kind",
    )
    source_kind: DataTypeSource = Field(
        description="Origin of the data type definition, e.g. franca, protobuf, etc.",
    )
    identifier: str = Field(
        description="Identifier of the data type definition in its source namespace",
    )
    namespace: str | None = Field(
        default=None,
        description="Optional namespace/module/package in which this data type is declared",
    )
    source_uri: FilePath | None = Field(
        default=None,
        description="Optional source file path which this data type definition was imported from",
    )
    deployment_properties: dict[str, object] = Field(
        default_factory=dict,
        description="Deployment properties aggregated from all communication bindings using this data type",
    )

    def model_post_init(self, context: Any, /) -> None:
        """Reject instantiation of this abstract base before registry insertion."""
        if type(self) is DataTypeBase:
            raise TypeError("DataTypeBase is abstract, instantiate a concrete data type")
        super().model_post_init(context)

    @classmethod
    def _get_language_spec(cls, source_kind: DataTypeSource) -> tuple[re.Pattern[str], re.Pattern[str], str]:
        """Return (identifier_pattern, namespace_pattern and separator) for the given source kind."""
        if source_kind == DataTypeSource.FRANCA:
            return FRANCA_IDENTIFIER_PATTERN, FRANCA_PACKAGE_PATTERN, FRANCA_SEPARATOR
        if source_kind == DataTypeSource.PROTOBUF:
            return PROTOBUF_IDENTIFIER_PATTERN, PROTOBUF_PACKAGE_PATTERN, PROTOBUF_SEPARATOR
        if source_kind == DataTypeSource.CPP_HEADER_FILE:
            return CPP_IDENTIFIER_PATTERN, CPP_NAMESPACE_PATTERN, CPP_SEPARATOR
        raise ValueError(f"Unsupported data type source kind: {source_kind}")

    @field_validator("identifier")
    @classmethod
    def _validate_name(cls, value: str, info: ValidationInfo) -> str:
        """Validate a type name according to the selected source-language identifier rules."""
        source_kind = info.data.get("source_kind")
        pattern, _, _ = cls._get_language_spec(source_kind)
        if not pattern.match(value):
            kind_name = getattr(source_kind, "name", str(source_kind))
            raise ValueError(
                f"Invalid {kind_name} identifier '{value}': must start with a letter or underscore, "
                "followed by letters, digits or underscores"
            )
        return value

    @field_validator("namespace")
    @classmethod
    def _validate_namespace(cls, value: str | None, info: ValidationInfo) -> str | None:
        """Validate a namespace/package path according to the selected source-language rules."""
        if value is None:
            return value

        source_kind = info.data.get("source_kind")
        _, pattern, separator = cls._get_language_spec(source_kind)
        if not pattern.match(value):
            kind_name = getattr(source_kind, "name", str(source_kind))
            raise ValueError(
                f"Invalid {kind_name} namespace / package '{value}': must contain valid identifiers separated by {separator}"
            )
        return value

    @property
    def fully_qualified_name(self) -> str:
        """Return the fully qualified name combining namespace and identifier."""
        if self.identifier is None:
            raise ValueError("Data types without an identifier do not have a fully qualified name")
        if not self.namespace:
            return self.identifier
        _, _, separator = self._get_language_spec(self.source_kind)
        return f"{self.namespace}{separator}{self.identifier}"


class DataTypeRef(EcuModelRef):
    """Reference to a declared data type definition by its unique model identifier."""

    def resolve(self) -> DataTypeBase:
        """Resolve this reference and ensure that it points to a data type definition."""
        element = super().resolve()
        if not isinstance(element, DataTypeBase):
            raise TypeError(f"Reference {self.target_id} points to {type(element).__name__}, expected DataTypeBase")
        return element


# Use site of a data type: either a builtin primitive or a reference to a declared definition.
TypeRef = PrimitiveType | DataTypeRef
