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

import re
from typing import Any

from pydantic import ConfigDict, Field, RootModel, field_validator
from pydantic_core import core_schema

from score.ecu_model.model import ModelElement

# Identifier syntax is the same across every supported IDL; only the namespace separator differs.
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class Identifier(RootModel[str]):
    """A single identifier, syntactically independent of the source IDL that declared it."""

    model_config = ConfigDict(frozen=True)

    root: str = Field(description="Identifier text, e.g. LaneInfo, speed_limit, uint32_t")

    @field_validator("root")
    @classmethod
    def _validate_root_is_an_identifier(cls, value: str) -> str:
        """Validate the identifier independently of any source IDL."""
        if not _IDENTIFIER_PATTERN.match(value):
            raise ValueError(
                f"Invalid identifier '{value}': must start with a letter or underscore, "
                "followed by letters, digits or underscores"
            )
        return value

    @property
    def as_str(self) -> str:
        return self.root

    def __str__(self) -> str:
        return self.as_str


class Namespace(tuple[Identifier, ...]):
    """Tuple-compatible namespace segments with convenient string rendering."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(cls, handler.generate_schema(tuple[Identifier, ...]))

    @property
    def as_str(self) -> str:
        return ".".join(str(segment) for segment in self)


class FullyQualifiedName(ModelElement):
    """An identifier together with its enclosing namespace, independent of the source IDL separator."""

    model_config = ConfigDict(frozen=True)

    identifier: Identifier = Field(description="Local identifier, e.g. Position")
    namespace: Namespace = Field(
        default=(),
        description="Enclosing namespace segments, outer-to-inner; empty for a name used without its namespace",
    )

    def render(self, separator: str) -> str:
        """Render the fully qualified name as text, joined by the given source-language separator."""
        return separator.join(str(segment) for segment in (*self.namespace, self.identifier))

    @property
    def as_str(self) -> str:
        return self.render(".")

    def __str__(self) -> str:
        return self.as_str
