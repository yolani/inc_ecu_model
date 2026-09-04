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
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.data_types.typedef import TypedefDataType


class TestTypedefDataType(unittest.TestCase):
    def test_creates_typedef_pointing_to_primitive(self) -> None:
        typedef = TypedefDataType(
            identifier="UserId",
            source_kind=DataTypeSource.FRANCA,
            data_type=PrimitiveDataType.UINT64,
        )

        self.assertEqual(typedef.kind, DataTypeKind.TYPEDEF)
        self.assertEqual(typedef.identifier, "UserId")
        self.assertEqual(typedef.data_type, PrimitiveDataType.UINT64)

    def test_supports_declared_type_ref_as_aliased_data_type(self) -> None:
        target_struct = StructDataType(identifier="Point", source_kind=DataTypeSource.FRANCA)
        typedef = TypedefDataType(
            identifier="PointAlias",
            source_kind=DataTypeSource.FRANCA,
            data_type=DataTypeRef(target_id=target_struct.id),
        )

        self.assertIsInstance(typedef.data_type, DataTypeRef)
        self.assertIs(typedef.data_type.resolve(), target_struct)


if __name__ == "__main__":
    unittest.main()
