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

from score.ecu_model.data_types.common import DataTypeBase, DataTypeKind, DataTypeSource


class TestProtobufValidation(unittest.TestCase):
    def test_protobuf_identifier_and_package_are_validated(self) -> None:
        DataTypeBase(
            kind=DataTypeKind.STRUCT,
            identifier="MyMessage",
            source_kind=DataTypeSource.PROTOBUF,
            namespace="com.example.sensor",
        )

        with self.assertRaises(ValueError):
            DataTypeBase(
                kind=DataTypeKind.STRUCT,
                identifier="1invalid",
                source_kind=DataTypeSource.PROTOBUF,
            )

        with self.assertRaises(ValueError):
            DataTypeBase(
                kind=DataTypeKind.STRUCT,
                identifier="MyMessage",
                source_kind=DataTypeSource.PROTOBUF,
                namespace="com..example",
            )

    def test_protobuf_fully_qualified_name(self) -> None:
        dt1 = DataTypeBase(
            kind=DataTypeKind.STRUCT,
            identifier="MyMessage",
            source_kind=DataTypeSource.PROTOBUF,
            namespace="com.example.sensor",
        )
        self.assertEqual(dt1.fully_qualified_name, "com.example.sensor.MyMessage")

        dt2 = DataTypeBase(
            kind=DataTypeKind.STRUCT,
            identifier="MyMessage",
            source_kind=DataTypeSource.PROTOBUF,
        )
        self.assertEqual(dt2.fully_qualified_name, "MyMessage")


if __name__ == "__main__":
    unittest.main()
