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

from collections.abc import Sequence
from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

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
    qualified_name: Identifier | FullyQualifiedName | None = Field(
        default=None,
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
        """Reject instantiation of this abstract base before registry insertion."""
        if type(self) is DataTypeBase:
            raise TypeError("DataTypeBase is abstract, instantiate a concrete data type")
        if self.qualified_name is None and self.kind != DataTypeKind.ARRAY:
            raise ValueError("Input should be a valid string: declared data types require an identifier")
        super().model_post_init(context)

    @model_validator(mode="before")
    @classmethod
    def _combine_identifier_and_namespace(cls, data: Any) -> Any:
        """Accept separate identifier/namespace constructor kwargs and combine them into `name`."""
        if not isinstance(data, dict) or ("identifier" not in data and "namespace" not in data and "name" not in data):
            return data
        if "name" in data and "identifier" not in data and "namespace" not in data:
            data["qualified_name"] = data.pop("name")
            return data
        identifier = data.pop("identifier", None)
        namespace = data.pop("namespace", None)
        source_kind = data.get("source_kind")
        if source_kind is None:
            source_kind_field = cls.model_fields.get("source_kind")
            source_kind = source_kind_field.default if source_kind_field is not None else None
        data["qualified_name"] = cls._qualify(identifier, namespace, source_kind)
        data.pop("name", None)
        return data

    @classmethod
    def _qualify(
        cls,
        identifier: Identifier | str | None,
        namespace: str | Sequence[Identifier | str] | None,
        source_kind: DataTypeSource | None,
    ) -> Identifier | FullyQualifiedName | None:
        """Combine an identifier with an optional namespace into a single name."""
        if namespace is None:
            return identifier
        if identifier is None:
            raise ValueError("namespace requires an identifier")
        segments = namespace.split(cls._get_separator(source_kind)) if isinstance(namespace, str) else namespace
        return FullyQualifiedName(
            identifier=cls._as_identifier(identifier),
            namespace=tuple(cls._as_identifier(segment) for segment in segments),
        )

    @staticmethod
    def _as_identifier(value: Identifier | str) -> Identifier:
        """Return the value as an Identifier, validating a plain string on the way."""
        return value if isinstance(value, Identifier) else Identifier(value)

    @classmethod
    def _get_separator(cls, source_kind: DataTypeSource) -> str:
        """Return the namespace separator used by the given source kind."""
        if source_kind == DataTypeSource.FRANCA:
            return "."
        if source_kind == DataTypeSource.PROTOBUF:
            return "."
        if source_kind == DataTypeSource.CPP_HEADER_FILE:
            return "::"
        raise ValueError(f"Unsupported data type source kind: {source_kind}")

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

    @property
    def identifier(self) -> Identifier | None:
        """Return the local identifier, independent of any enclosing namespace."""
        return (
            self.qualified_name.identifier
            if isinstance(self.qualified_name, FullyQualifiedName)
            else self.qualified_name
        )

    @property
    def name(self) -> Identifier | None:
        """Return the local identifier for compatibility with the former data type model."""
        return self.identifier

    @property
    def namespace(self) -> tuple[Identifier, ...] | None:
        """Return the enclosing namespace segments, or None if the name is unqualified."""
        return self.qualified_name.namespace if isinstance(self.qualified_name, FullyQualifiedName) else None

    @namespace.setter
    def namespace(self, namespace: str | Sequence[Identifier | str] | None) -> None:
        """Requalify the existing identifier, for producers that learn the namespace only later."""
        self.qualified_name = self._qualify(self.identifier, namespace, self.source_kind)

    @property
    def fully_qualified_name(self) -> str:
        """Return the fully qualified name combining namespace and identifier."""
        if self.qualified_name is None:
            raise ValueError("Data types without an identifier do not have a fully qualified name")
        if isinstance(self.qualified_name, FullyQualifiedName):
            return self.qualified_name.render(self._get_separator(self.source_kind))
        return str(self.qualified_name)


# Use site of a data type: either a builtin primitive or a direct reference to a declared definition.
DataType = PrimitiveDataType | DataTypeBase

# Name of a data type declaration that is not resolvable yet, e.g. while a parser is still reading its sources.
DataTypeReference = Identifier | FullyQualifiedName

# Use site that may temporarily hold an unresolved reference until model resolution has completed.
# A plain string is validated as an unresolved reference; primitives must be passed as PrimitiveDataType members.
DataTypeOrReference = DataType | DataTypeReference
