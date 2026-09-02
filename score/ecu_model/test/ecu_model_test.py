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

import pickle
import unittest
from uuid import UUID, uuid4

from pydantic import ValidationError

from score.ecu_model.ecu_model import EcuModel, EcuModelElement


class TestEcuModel(unittest.TestCase):
    def test_root_instantiation_succeeds(self) -> None:
        root = EcuModel()
        self.assertIsInstance(root, EcuModel)

    def test_root_instance_is_not_registered(self) -> None:
        root = EcuModel()
        self.assertNotIn(root, EcuModel.model_registry.values())


class TestEcuModelElement(unittest.TestCase):
    def test_default_fields(self) -> None:
        element = EcuModelElement()
        self.assertIsInstance(element.id, UUID)
        self.assertEqual(element.description, "")

    def test_custom_description(self) -> None:
        element = EcuModelElement(description="Another test element")
        self.assertEqual(element.description, "Another test element")

    def test_registered_in_model_registry(self) -> None:
        element = EcuModelElement()
        self.assertIs(EcuModel.model_registry[element.id], element)

    def test_duplicate_id_raises_validation_error(self) -> None:
        shared_id = uuid4()
        EcuModelElement(id=shared_id)
        with self.assertRaises(ValidationError):
            EcuModelElement(id=shared_id)

    def test_str_representation(self) -> None:
        element = EcuModelElement(description="desc")
        self.assertEqual(str(element), f"EcuModelElement(id={element.id}, description=desc)")

    def test_assignment_is_validated(self) -> None:
        element = EcuModelElement()
        element.description = "updated"
        self.assertEqual(element.description, "updated")

    def test_invalid_assignment_raises_validation_error(self) -> None:
        element = EcuModelElement()
        with self.assertRaises(ValidationError):
            element.id = "not-a-uuid"

    def test_existing_instance_is_revalidated(self) -> None:
        # model_construct() bypasses validators, so this instance holds an invalid id undetected.
        bypassed = EcuModelElement.model_construct(id="not-a-uuid", description="desc")
        with self.assertRaises(ValidationError):
            EcuModelElement.model_validate(bypassed)


class TestSerialization(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_registry = dict(EcuModel.model_registry)
        EcuModel.model_registry.clear()

    def tearDown(self) -> None:
        EcuModel.model_registry.clear()
        EcuModel.model_registry.update(self._saved_registry)

    def test_round_trip_restores_all_elements(self) -> None:
        elements = [EcuModelElement(description="first"), EcuModelElement(description="second")]
        blob = EcuModel.serialize()
        EcuModel.model_registry.clear()

        self.assertEqual(EcuModel.deserialize(blob), 2)
        for element in elements:
            restored = EcuModel.model_registry[element.id]
            self.assertIsNot(restored, element)
            self.assertEqual(restored.description, element.description)

    def test_deserialize_detaches_pre_existing_instances(self) -> None:
        original = EcuModelElement(description="original")
        blob = EcuModel.serialize()
        squatter = EcuModelElement(description="squatter")
        EcuModel.model_registry[original.id] = squatter

        EcuModel.deserialize(blob)

        restored = EcuModel.model_registry[original.id]
        self.assertEqual(restored.description, "original")
        self.assertIsNot(restored, original)

    def test_deserialize_drops_elements_absent_from_the_payload(self) -> None:
        blob = EcuModel.serialize()
        orphan = EcuModelElement()

        EcuModel.deserialize(blob)

        self.assertNotIn(orphan.id, EcuModel.model_registry)

    def test_malformed_payload_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            EcuModel.deserialize(pickle.dumps({"not": "a registry"}))


if __name__ == "__main__":
    unittest.main()
