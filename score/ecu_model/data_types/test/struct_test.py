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

from score.ecu_model.data_types.common import DataTypeKind, DataTypeRef, DataTypeSource
from score.ecu_model.data_types.composite import DataTypeField
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.ecu_model import EcuModelRef


class TestStructDataType(unittest.TestCase):
    @staticmethod
    def _field_ref(
        identifier: str,
        data_type: PrimitiveDataType | DataTypeRef = PrimitiveDataType.UINT32,
        field_number: int | None = None,
    ) -> EcuModelRef:
        field = DataTypeField(identifier=identifier, data_type=data_type, field_number=field_number)
        return EcuModelRef(target_id=field.id)

    def test_keeps_declared_fields_in_order(self) -> None:
        data_type = StructDataType(
            identifier="Position",
            source_kind=DataTypeSource.PROTOBUF,
            fields=[self._field_ref("x", field_number=1), self._field_ref("y", field_number=2)],
        )

        self.assertEqual(data_type.kind, DataTypeKind.STRUCT)
        self.assertIsInstance(data_type.fields, tuple)
        self.assertEqual(data_type.fields[0].identifier, "x")
        self.assertEqual(data_type.fields[1].identifier, "y")

    def test_defaults_to_a_required_field_without_wire_tag(self) -> None:
        field = DataTypeField(identifier="x", data_type=PrimitiveDataType.UINT32)

        self.assertIsNone(field.field_number)
        self.assertFalse(field.optional)
        self.assertEqual(field.deployment_properties, {})

    def test_supports_declared_data_types_as_field_type(self) -> None:
        nested = StructDataType(identifier="Position", source_kind=DataTypeSource.FRANCA)
        data_type = StructDataType(
            identifier="Pose",
            source_kind=DataTypeSource.FRANCA,
            fields=[self._field_ref("position", DataTypeRef(target_id=nested.id))],
        )

        self.assertIs(data_type.fields[0].resolve().data_type.resolve(), nested)

    def test_prevents_in_place_field_mutation(self) -> None:
        data_type = StructDataType(
            identifier="Position",
            source_kind=DataTypeSource.FRANCA,
            fields=[self._field_ref("x")],
        )

        with self.assertRaises(AttributeError):
            data_type.fields.append(self._field_ref("y"))  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
