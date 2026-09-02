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
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from score.ecu_model.data_types.common import (
    DataTypeBase,
    DataTypeKind,
    DataTypeRef,
    DataTypeSource,
    TypeRef,
)
from score.ecu_model.data_types.primitives import PrimitiveType
from score.ecu_model.ecu_model import EcuModel, EcuModelElement, EcuModelRef


class StructMember(BaseModel):
    """Minimal struct member used to exercise type references in the tests."""

    identifier: str
    type: TypeRef


class StructDataType(DataTypeBase):
    """Minimal struct definition used to exercise type references in the tests."""

    kind: Literal[DataTypeKind.STRUCT] = Field(default=DataTypeKind.STRUCT, frozen=True)
    members: list[StructMember] = Field(default_factory=list)


class TestDataTypeKind(unittest.TestCase):
    def test_primitive_is_not_a_declarable_kind(self) -> None:
        self.assertNotIn("primitive", {kind.value for kind in DataTypeKind})

    def test_kind_and_source_str_representation(self) -> None:
        self.assertEqual(str(DataTypeKind.STRUCT), "struct")
        self.assertEqual(str(DataTypeSource.FRANCA), "franca")
        self.assertEqual(str(DataTypeSource.CPP_HEADER_FILE), "cpp_header_file")


class TestDataTypeBaseCommon(unittest.TestCase):
    def test_unsupported_source_kind_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            DataTypeBase._get_language_spec("unsupported_source_kind")  # type: ignore[arg-type]

    def test_optional_fields_defaults_and_values(self) -> None:
        data_type = StructDataType(
            kind=DataTypeKind.STRUCT,
            identifier="MyStruct",
            source_kind=DataTypeSource.FRANCA,
            deployment_properties={"key": "value"},
        )
        self.assertIsNone(data_type.source_uri)
        self.assertEqual(data_type.deployment_properties, {"key": "value"})

    def test_rejects_direct_instantiation(self) -> None:
        with self.assertRaisesRegex(TypeError, "DataTypeBase is abstract"):
            DataTypeBase(
                kind=DataTypeKind.STRUCT,
                identifier="MyStruct",
                source_kind=DataTypeSource.FRANCA,
            )


class TestTypeRef(unittest.TestCase):
    adapter = TypeAdapter(TypeRef)

    def test_primitive_is_referenced_by_canonical_name(self) -> None:
        self.assertIs(self.adapter.validate_python("uint32"), PrimitiveType.UINT32)

    def test_declared_type_is_referenced_by_identifier(self) -> None:
        target_id = uuid4()

        ref = self.adapter.validate_python({"target_id": str(target_id)})

        self.assertEqual(ref, DataTypeRef(target_id=target_id))

    def test_unknown_primitive_name_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.adapter.validate_python("uint24")

    def test_round_trip_keeps_both_variants_distinguishable(self) -> None:
        for ref in (PrimitiveType.UINT32, DataTypeRef(target_id=uuid4())):
            with self.subTest(ref=ref):
                dumped = self.adapter.dump_python(ref)

                self.assertEqual(self.adapter.validate_python(dumped), ref)


class TestDataTypeRefResolution(unittest.TestCase):
    def test_resolves_registered_definition(self) -> None:
        definition = StructDataType(identifier="Position", source_kind=DataTypeSource.FRANCA)

        resolved = DataTypeRef(target_id=definition.id).resolve()

        self.assertIs(resolved, definition)

    def test_unknown_identifier_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            DataTypeRef(target_id=uuid4()).resolve()

    def test_reference_to_foreign_element_raises_type_error(self) -> None:
        element = EcuModelElement()

        with self.assertRaises(TypeError):
            DataTypeRef(target_id=element.id).resolve()

    def test_reference_survives_definition_that_does_not_exist_yet(self) -> None:
        ref = DataTypeRef(target_id=uuid4())

        definition = StructDataType(id=ref.target_id, identifier="Gear", source_kind=DataTypeSource.FRANCA)

        self.assertIs(ref.resolve(), definition)


class TestEcuModelRefResolution(unittest.TestCase):
    def test_resolves_registered_model_element(self) -> None:
        element = EcuModelElement()

        self.assertIs(EcuModelRef(target_id=element.id).resolve(), element)


class TestPickleRoundTrip(unittest.TestCase):
    """Example: persist the whole type graph and make it resolvable again."""

    def setUp(self) -> None:
        self._saved_registry = dict(EcuModel.model_registry)
        EcuModel.model_registry.clear()

    def tearDown(self) -> None:
        EcuModel.model_registry.clear()
        EcuModel.model_registry.update(self._saved_registry)

    @staticmethod
    def _build_type_graph() -> tuple[DataTypeBase, DataTypeBase]:
        position = StructDataType(
            identifier="Position",
            namespace="app.geometry",
            source_kind=DataTypeSource.FRANCA,
            members=[
                StructMember(identifier="x", type=PrimitiveType.FLOAT),
                StructMember(identifier="y", type=PrimitiveType.FLOAT),
            ],
        )
        waypoint = StructDataType(
            identifier="Waypoint",
            namespace="app.routing",
            source_kind=DataTypeSource.FRANCA,
            members=[
                StructMember(identifier="position", type=DataTypeRef(target_id=position.id)),
                StructMember(identifier="index", type=PrimitiveType.UINT32),
            ],
        )
        return position, waypoint

    def test_references_resolve_again_after_round_trip(self) -> None:
        position, waypoint = self._build_type_graph()
        blob = EcuModel.serialize()
        EcuModel.model_registry.clear()  # simulate loading into a fresh process

        self.assertEqual(EcuModel.deserialize(blob), 2)

        restored_waypoint = EcuModel.model_registry[waypoint.id]
        assert isinstance(restored_waypoint, StructDataType)
        member = restored_waypoint.members[0]
        assert isinstance(member.type, DataTypeRef)

        self.assertIs(member.type.resolve(), EcuModel.model_registry[position.id])
        self.assertIsNot(member.type.resolve(), position)

    def test_round_trip_preserves_identifiers_and_primitive_members(self) -> None:
        position, _ = self._build_type_graph()
        blob = EcuModel.serialize()
        EcuModel.model_registry.clear()

        EcuModel.deserialize(blob)

        restored = EcuModel.model_registry[position.id]
        assert isinstance(restored, StructDataType)
        self.assertEqual(restored.identifier, "Position")
        self.assertEqual(restored.members[0].type, PrimitiveType.FLOAT)


if __name__ == "__main__":
    unittest.main()
