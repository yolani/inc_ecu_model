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
"""Franca name values kept separate from the strict data model identifiers."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValidIdentifier:
    """Franca identifier, including escaped keywords and source-level spelling."""

    root: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.replace("^", ""))

    @property
    def as_str(self) -> str:
        return self.root

    def __str__(self) -> str:
        return self.root


@dataclass(frozen=True)
class FullyQualifiedName:
    """Franca qualified name; segments may be retained for parser resolution."""

    names: list[ValidIdentifier] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "names",
            [name if isinstance(name, ValidIdentifier) else ValidIdentifier(str(name)) for name in self.names],
        )

    @property
    def identifier(self) -> str:
        """Return the complete source-level name used by legacy FDEPL consumers."""
        return self.as_str

    @property
    def as_str(self) -> str:
        return ".".join(name.as_str for name in self.names)

    @property
    def as_path(self) -> str:
        return "/".join(name.as_str for name in self.names)

    def __str__(self) -> str:
        return self.as_str
