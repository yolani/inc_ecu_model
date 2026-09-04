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

from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from score.ecu_model.data_types.common import DataTypeKind, DataTypeSource
from score.ecu_model.data_types.external import ExternalDataType


class TestExternalDataType(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.header_path = Path(self.temp_dir.name) / "types.h"
        self.header_path.write_text("// dummy header", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_creates_external_data_type(self) -> None:
        data_type = ExternalDataType(
            identifier="AbortTransfer",
            namespace="adp::managed_data_transfer",
            header=self.header_path,  # type: ignore[arg-type]
        )

        self.assertEqual(data_type.kind, DataTypeKind.EXTERNAL)
        self.assertEqual(data_type.source_kind, DataTypeSource.CPP_HEADER_FILE)
        self.assertEqual(data_type.identifier, "AbortTransfer")
        self.assertEqual(data_type.namespace, "adp::managed_data_transfer")
        self.assertEqual(data_type.fully_qualified_name, "adp::managed_data_transfer::AbortTransfer")
        self.assertEqual(data_type.header, self.header_path)

    def test_rejects_non_existent_header(self) -> None:
        non_existent = Path(self.temp_dir.name) / "non_existent.h"
        with self.assertRaises(ValidationError) as ctx:
            ExternalDataType(
                identifier="Point",
                header=non_existent,  # type: ignore[arg-type]
            )
        self.assertIn("Path does not point to a file", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
