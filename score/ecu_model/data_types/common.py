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
from typing import Any

from pydantic import Field, field_validator

from score.ecu_model.data_types.identifier import FullyQualifiedName, Identifier
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.model import ModelElement


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
    EXTERNAL = "external"

    def __str__(self) -> str:
        """Return the canonical data type kind name."""
        return self.value


class DataTypeSource(str, Enum):
    """IDL (Interface Definition Language) from which the data type originates."""

    FRANCA = "franca"
    PROTOBUF = "protobuf"
    CPP_HEADER_FILE = "cpp_header_file"

    @property
    def separator(self) -> str:
        """Return the namespace separator used by this source language."""
        return "::" if self is DataTypeSource.CPP_HEADER_FILE else "."

    def __str__(self) -> str:
        """Return the canonical data type source name."""
        return self.value


class DataTypeBase(ModelElement):
    """Shared metadata for data types that are declared in a source language."""

    kind: DataTypeKind = Field(
        description="Discriminator identifying the concrete data type definition kind",
    )
    source_kind: DataTypeSource = Field(
        description="Origin of the data type definition, e.g. franca, protobuf, etc.",
    )
    qualified_name: Identifier | FullyQualifiedName = Field(
        description="Identifier of the data type, optionally qualified by its enclosing namespace",
    )
    source_uri: str | None = Field(
        default=None,
        description="Optional source file path which this data type definition was imported from",
    )
    deployment_properties: dict[str, object] = Field(
        default_factory=dict,
        description="Deployment properties aggregated from all communication bindings using this data type",
    )

    def model_post_init(self, context: Any, /) -> None:
        """Reject direct instantiation of the abstract base type."""
        if type(self) is DataTypeBase:
            raise TypeError("DataTypeBase is abstract, instantiate a concrete data type")
        super().model_post_init(context)

    @field_validator("source_uri")
    @classmethod
    def _validate_source_uri(cls, value: str | None) -> str | None:
        """Validate that source_uri is non-empty and contains no null bytes when provided."""
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("source_uri must not be empty when provided")
        if "\x00" in stripped:
            raise ValueError("source_uri must not contain null bytes")
        return stripped

    # TODO: cleanup the following properties for backwards compatibility with the former data type model.
    @property
    def identifier(self) -> Identifier | None:
        """Return the local identifier, independent of any enclosing namespace."""
        return getattr(self.qualified_name, "identifier", self.qualified_name)

    @property
    def name(self) -> Identifier | None:
        """Return the local identifier for compatibility with the former data type model."""
        return self.identifier

    @property
    def namespace(self) -> tuple[Identifier, ...] | None:
        """Return the enclosing namespace segments, or None if the name is unqualified."""
        return self.qualified_name.namespace if isinstance(self.qualified_name, FullyQualifiedName) else None

    @property
    def fully_qualified_name(self) -> str:
        """Return the fully qualified name combining namespace and identifier."""
        if self.qualified_name is None:
            raise ValueError("Data types without an identifier do not have a fully qualified name")
        return (
            self.qualified_name.render(self.source_kind.separator)
            if isinstance(self.qualified_name, FullyQualifiedName)
            else str(self.qualified_name)
        )


# Use site of a data type: either a builtin primitive or a direct reference to a declared definition.
DataType = PrimitiveDataType | DataTypeBase

# Name of a data type declaration that is not resolvable yet, e.g. while a parser is still reading its sources.
DataTypeReference = Identifier | FullyQualifiedName

# Use site that may temporarily hold an unresolved reference until model resolution has completed.
# A plain string is validated as an unresolved reference; primitives must be passed as PrimitiveDataType members.
DataTypeOrReference = DataType | DataTypeReference
