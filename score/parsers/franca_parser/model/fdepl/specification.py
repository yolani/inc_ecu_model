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

"""Internal models for FDEPL deployment specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from score.parsers.franca_parser.model.franca_name_types import (
    FullyQualifiedName,
    ValidIdentifier,
)


class DeploymentPropertyType(str, Enum):
    """Supported FDEPL deployment property value types."""

    INTEGER = "Integer"
    STRING = "String"
    BOOLEAN = "Boolean"
    INTERFACE = "Interface"
    ENUM = "Enum"
    EXTENSION = "Extension"


class PropertyFlag(str, Enum):
    """Requirement behavior for a deployment property declaration."""

    MANDATORY = "mandatory"
    OPTIONAL = "optional"
    DEFAULT = "default"


@dataclass
class ParameterLiability:
    """Optionality or default value associated with a property declaration."""

    property_flag: PropertyFlag
    default_value: int | str | bool | ValidIdentifier | list[object] | None = None


@dataclass
class DeploymentPropertyTypeReference:
    """Allowed value type and modifiers for a deployment property."""

    property_type: DeploymentPropertyType
    is_array: bool = False
    extension: ValidIdentifier | None = None
    enumerators: list[ValidIdentifier] = field(default_factory=list)


@dataclass
class ParameterDeclaration:
    """One deployment property declared for a deployment host."""

    host: str
    name: ValidIdentifier
    type_reference: DeploymentPropertyTypeReference
    liabilities: list[ParameterLiability] = field(default_factory=list)


@dataclass
class DeploymentSpecification:
    """Named FDEPL specification and its property declarations by host."""

    name: FullyQualifiedName
    base_specifications: list[FullyQualifiedName | "DeploymentSpecification"] = field(default_factory=list)
    hosts: dict[str, dict[str, ParameterDeclaration]] = field(default_factory=dict)
