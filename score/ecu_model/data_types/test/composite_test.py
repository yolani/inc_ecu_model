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

from score.ecu_model.data_types.common import DataTypeKind, DataTypeSource
from score.ecu_model.data_types.composite import CompositeDataType, DataTypeField
from score.ecu_model.data_types.primitives import PrimitiveType
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.ecu_model import EcuModel, EcuModelRef


class TestCompositeDataType(unittest.TestCase):
    @staticmethod
    def _field_ref(identifier: str, field_number: int | None = None) -> EcuModelRef:
        field = DataTypeField(
            identifier=identifier,
            data_type=PrimitiveType.UINT32,
            field_number=field_number,
        )
        return EcuModelRef(target_id=field.id)

    def test_rejects_direct_instantiation_of_the_abstract_base(self) -> None:
        with self.assertRaisesRegex(TypeError, "CompositeDataType is abstract"):
            CompositeDataType(
                identifier="Position",
                kind=DataTypeKind.STRUCT,
                source_kind=DataTypeSource.FRANCA,
            )

    def test_does_not_register_the_rejected_instance(self) -> None:
        registered_elements = len(EcuModel.model_registry)

        with self.assertRaises(TypeError):
            CompositeDataType(
                identifier="Position",
                kind=DataTypeKind.STRUCT,
                source_kind=DataTypeSource.FRANCA,
            )

        self.assertEqual(len(EcuModel.model_registry), registered_elements)

    def test_rejects_invalid_or_duplicate_field_identifiers(self) -> None:
        with self.assertRaisesRegex(ValidationError, "Invalid FRANCA field identifier '1field'"):
            StructDataType(
                identifier="Position",
                source_kind=DataTypeSource.FRANCA,
                fields=[self._field_ref("1field")],
            )

        with self.assertRaisesRegex(ValidationError, "field identifiers must be unique"):
            StructDataType(
                identifier="Position",
                source_kind=DataTypeSource.FRANCA,
                fields=[self._field_ref("field"), self._field_ref("field")],
            )

    def test_rejects_inconsistent_or_duplicate_field_numbers(self) -> None:
        with self.assertRaisesRegex(
            ValidationError, "field numbers must either all be explicitly defined or all be omitted"
        ):
            StructDataType(
                identifier="Position",
                source_kind=DataTypeSource.PROTOBUF,
                fields=[self._field_ref("x", 1), self._field_ref("y")],
            )

        with self.assertRaisesRegex(ValidationError, "explicit field numbers must be unique"):
            StructDataType(
                identifier="Position",
                source_kind=DataTypeSource.PROTOBUF,
                fields=[self._field_ref("x", 1), self._field_ref("y", 1)],
            )

    def test_rejects_invalid_field_numbers(self) -> None:
        with self.assertRaisesRegex(ValidationError, "field number must be positive"):
            DataTypeField(identifier="field", data_type=PrimitiveType.UINT32, field_number=0)

        with self.assertRaisesRegex(ValidationError, "field number must be an integer, not boolean"):
            DataTypeField(identifier="field", data_type=PrimitiveType.UINT32, field_number=True)

    def test_revalidates_fields_on_assignment(self) -> None:
        data_type = StructDataType(
            identifier="Position",
            source_kind=DataTypeSource.FRANCA,
            fields=[self._field_ref("field")],
        )

        with self.assertRaisesRegex(ValidationError, "field identifiers must be unique"):
            data_type.fields = (self._field_ref("field"), self._field_ref("field"))

    def test_allows_franca_inheritance_only(self) -> None:
        parent = StructDataType(identifier="BasePosition", source_kind=DataTypeSource.FRANCA)
        child = StructDataType(
            identifier="Position",
            source_kind=DataTypeSource.FRANCA,
            extends={"target_id": parent.id},
        )
        self.assertIs(child.extends.resolve(), parent)

        with self.assertRaisesRegex(
            ValidationError, "StructDataType inheritance is only allowed for FRANCA source kind"
        ):
            StructDataType(
                identifier="Position",
                source_kind=DataTypeSource.PROTOBUF,
                extends={"target_id": parent.id},
            )


if __name__ == "__main__":
    unittest.main()
