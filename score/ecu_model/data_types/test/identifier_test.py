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

import unittest

from pydantic import ValidationError

from score.ecu_model.data_types.identifier import FullyQualifiedName, Identifier


class TestIdentifier(unittest.TestCase):
    def test_accepts_a_valid_identifier(self) -> None:
        self.assertEqual(str(Identifier("_value2")), "_value2")

    def test_rejects_an_invalid_identifier(self) -> None:
        with self.assertRaisesRegex(ValidationError, "Invalid identifier 'with-dash'"):
            Identifier("with-dash")

    def test_is_hashable_and_comparable_by_value(self) -> None:
        self.assertEqual(Identifier("Position"), Identifier("Position"))
        self.assertEqual(len({Identifier("Position"), Identifier("Position")}), 1)


class TestFullyQualifiedName(unittest.TestCase):
    def test_parses_and_renders_with_the_given_separator(self) -> None:
        name = FullyQualifiedName(
            identifier=Identifier("Position"),
            namespace=(Identifier("app"), Identifier("geometry")),
        )

        self.assertEqual(name.as_str, "app.geometry.Position")
        self.assertEqual(name.render("::"), "app::geometry::Position")

    def test_rejects_a_name_without_segments(self) -> None:
        with self.assertRaisesRegex(ValidationError, "needs at least one segment"):
            FullyQualifiedName(names=[])

    def test_round_trips_a_flat_segment_sequence(self) -> None:
        name = FullyQualifiedName(names=["app", "geometry", "Position"])

        self.assertEqual(name.as_str, "app.geometry.Position")
        self.assertEqual(name.names, [Identifier("app"), Identifier("geometry"), Identifier("Position")])
        self.assertEqual(name.namespace.as_str, "app.geometry")

    def test_renders_a_name_used_without_its_namespace(self) -> None:
        name = FullyQualifiedName(names=["Position"])

        self.assertEqual(name.as_str, "Position")
        self.assertEqual(name.namespace, ())


if __name__ == "__main__":
    unittest.main()
