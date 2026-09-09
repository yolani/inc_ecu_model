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

"""Common Lark node transformations for Franca source files."""

from lark import Transformer, v_args

from score.parsers.franca_parser.model.franca_name_types import FullyQualifiedName, ValidIdentifier


def franca_identifier(name: object) -> ValidIdentifier:
    """Build an identifier from a Franca token, dropping the marker that escapes reserved keywords."""
    return ValidIdentifier(str(name))


class FrancaFileTransformer(Transformer):
    """Base Lark transformer for a single Franca source file."""

    @staticmethod
    def fi_fqn(names: list[ValidIdentifier]) -> FullyQualifiedName:
        """Build a Franca fully qualified name."""
        return FullyQualifiedName(names=names)

    @staticmethod
    @v_args(inline=True)
    def f_valid_id(name: object) -> ValidIdentifier:
        """Build a validated Franca identifier."""
        return franca_identifier(name)

    @staticmethod
    @v_args(inline=True)
    def fi_keywords(keyword: object) -> ValidIdentifier:
        """Build an escaped Franca keyword identifier."""
        return franca_identifier(keyword)
