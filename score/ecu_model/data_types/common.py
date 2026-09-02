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
from uuid import UUID

from pydantic import BaseModel, Field

from score.ecu_model.data_types.primitives import PrimitiveType
from score.ecu_model.ecu_model import EcuModel, EcuModelElement


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


class DataTypeBase(EcuModelElement):
    """Shared metadata for data types that are declared in a source language."""

    kind: DataTypeKind = Field(
        description="Discriminator identifying the concrete data type definition kind",
    )
    # TODO replace with proper identifier object from orion repo
    name: str = Field(
        description="Name of the data type definition in its source namespace",
    )
    # TODO replace with proper namespace object from orion repo
    namespace: str | None = Field(
        default=None,
        description="Optional namespace/module/package in which this data type is declared",
    )
    # TODO replace with proper enum
    source_kind: str | None = Field(
        default=None,
        description="Origin of the data type definition, e.g. franca, protobuf",
    )
    source_uri: str | None = Field(
        default=None,
        description="Optional source file URI/path where this data type definition was imported from",
    )
    deployment_properties: dict[str, object] = Field(
        default_factory=dict,
        description="Deployment properties aggregated from all communication bindings using this data type",
    )


class DataTypeRef(BaseModel):
    """Reference to a declared data type definition by its unique model identifier."""

    target_id: UUID = Field(
        description="Identifier of the referenced data type definition",
    )

    def resolve(self) -> DataTypeBase:
        """
        Look the referenced data type definition up in the EcuModel registry.

        Resolution is deliberately lazy: a reference may be deserialized before its definition exists.

        Raises:
            KeyError: If no model element with the referenced identifier is registered.
            TypeError: If the referenced model element is not a data type definition.
        """
        element = EcuModel.model_registry.get(self.target_id)
        if element is None:
            raise KeyError(f"Unresolved data type reference {self.target_id}")
        if not isinstance(element, DataTypeBase):
            raise TypeError(f"Reference {self.target_id} points to {type(element).__name__}, expected DataTypeBase")
        return element


# Use site of a data type: either a builtin primitive or a reference to a declared definition.
TypeRef = PrimitiveType | DataTypeRef
