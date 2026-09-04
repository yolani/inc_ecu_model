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
from score.ecu_model.data_types.map import MapDataType
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType


class TestMapDataType(unittest.TestCase):
    def test_creates_map_data_type(self) -> None:
        map_type = MapDataType(
            identifier="StringToIntMap",
            source_kind=DataTypeSource.FRANCA,
            key_type=PrimitiveDataType.STRING,
            value_type=PrimitiveDataType.INT32,
        )

        self.assertEqual(map_type.kind, DataTypeKind.MAP)
        self.assertEqual(map_type.identifier, "StringToIntMap")
        self.assertEqual(map_type.key_type, PrimitiveDataType.STRING)
        self.assertEqual(map_type.value_type, PrimitiveDataType.INT32)

    def test_supports_declared_type_ref_as_key_or_value_type(self) -> None:
        value_struct = StructDataType(identifier="Payload", source_kind=DataTypeSource.FRANCA)
        map_type = MapDataType(
            identifier="PayloadMap",
            source_kind=DataTypeSource.FRANCA,
            key_type=PrimitiveDataType.STRING,
            value_type=DataTypeRef(target_id=value_struct.id),
        )

        self.assertIsInstance(map_type.value_type, DataTypeRef)
        self.assertIs(map_type.value_type.resolve(), value_struct)


if __name__ == "__main__":
    unittest.main()
