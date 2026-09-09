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

"""Lark transformer for a single FIDL source file."""

from collections.abc import Callable
from dataclasses import dataclass

from lark import Token, v_args

from score.ecu_model.data_types.array import ArrayDataType
from score.ecu_model.data_types.common import (
    DataTypeBase,
    DataTypeOrReference,
    DataTypeSource,
)
from score.ecu_model.data_types.composite import DataTypeField
from score.ecu_model.data_types.enum import EnumDataType, EnumValue
from score.ecu_model.data_types.identifier import FullyQualifiedName as ModelFullyQualifiedName, Identifier
from score.ecu_model.data_types.map import MapDataType
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType
from score.ecu_model.data_types.typedef import TypedefDataType
from score.ecu_model.data_types.union import UnionDataType
from score.parsers.franca_parser.model.fidl.fidl_file import FIDLFileModel
from score.parsers.franca_parser.model.franca_name_types import (
    FullyQualifiedName,
    ValidIdentifier,
)
from score.parsers.franca_parser.model.franca_file import (
    FrancaFileModel,
    FrancaTransformationContext,
)
from score.parsers.franca_parser.model.fidl.type_collection import (
    TypeCollection,
)
from score.parsers.franca_parser.model.parsed_file import ParsedFile
from score.parsers.franca_parser.transformer.base_transformer import (
    FrancaFileTransformer,
)
from score.parsers.franca_parser.transformer.resolver.fidl_datatype_resolver import FIDLDataTypeResolver
from score.parsers.franca_parser.transformer.resolver.fidl_datatype_resolver import (
    PendingDatatypeReference,
)


PRIMITIVE_TYPES = {
    "boolean": PrimitiveDataType.BOOL,
    "string": PrimitiveDataType.STRING,
    "bytebuffer": PrimitiveDataType.BYTES,
    "double": PrimitiveDataType.DOUBLE,
    "float": PrimitiveDataType.FLOAT,
    "uint8": PrimitiveDataType.UINT8,
    "uint16": PrimitiveDataType.UINT16,
    "uint32": PrimitiveDataType.UINT32,
    "uint64": PrimitiveDataType.UINT64,
    "int8": PrimitiveDataType.INT8,
    "int16": PrimitiveDataType.INT16,
    "int32": PrimitiveDataType.INT32,
    "int64": PrimitiveDataType.INT64,
}

# Grammar elements that may end up in a data type slot: a builtin, a declaration, or a not yet resolved name.
_DATA_TYPE_ELEMENTS = (FullyQualifiedName, DataTypeBase, PrimitiveDataType)


@dataclass(frozen=True)
class _EnumLiteral:
    """Enum literal before its implicit value is known; EnumValue is immutable and needs the value up front."""

    identifier: Identifier
    value: int | None


class FIDLTransformer(FrancaFileTransformer):
    """Transform one FIDL source file into declaration models."""

    def __init__(
        self,
        transformed_files: dict[object, FrancaFileModel],
        transformation_context: FrancaTransformationContext,
    ) -> None:
        """Create a transformer with declarations visible from completed imports."""
        super().__init__()
        self._transformed_files = transformed_files
        self._import_resolver = FIDLDataTypeResolver(transformed_files)
        self._transformation_context = transformation_context
        self._pending_datatype_references_by_declaration: dict[int, list[PendingDatatypeReference]] = {}
        self._pending_datatype_references: list[PendingDatatypeReference] = []
        self._parser_reference_by_model_reference: dict[int, FullyQualifiedName] = {}

    @property
    def pending_datatype_references(self) -> list[PendingDatatypeReference]:
        """Return datatype references unresolved after local FIDL resolution."""
        return self._pending_datatype_references

    def transform_file(self, parsed_file: ParsedFile) -> FIDLFileModel:
        """Produce the file model available to dependent FIDL transformations."""
        file_model = self.transform(parsed_file.parse_tree)
        file_model.file_path = parsed_file.file_path
        file_model.imported_files = parsed_file.imports
        self._apply_declaration_metadata(file_model)
        return file_model

    def _to_model_reference(self, element: object) -> object:
        """Convert a parser FQN into a valid model identifier and retain its source spelling."""
        if not isinstance(element, FullyQualifiedName):
            return element
        model_reference = Identifier("_".join(name.as_str for name in element.names))
        self._parser_reference_by_model_reference[id(model_reference)] = element
        return model_reference

    @staticmethod
    def _to_parser_reference(element: Identifier) -> FullyQualifiedName:
        """Convert a strict model reference back to the parser's FQN shape."""
        if isinstance(element, Identifier):
            return FullyQualifiedName(names=[ValidIdentifier(element.as_str)])
        return FullyQualifiedName(names=[ValidIdentifier(element.as_str)])

    @staticmethod
    def _declaration_namespace(
        package: FullyQualifiedName,
        collection: TypeCollection,
    ) -> FullyQualifiedName:
        """Return the namespace of declarations owned by one type collection."""
        names = list(package.names)
        if collection.name is not None:
            names.append(collection.name)
        return FullyQualifiedName(names=names)

    @classmethod
    def _apply_declaration_metadata(cls, file_model: FIDLFileModel) -> None:
        """Assign metadata shared by declarations in each type collection."""
        for collection in file_model.type_collections:
            namespace = cls._declaration_namespace(file_model.namespace, collection)
            for datatype in collection.datatypes:
                datatype.qualified_name = ModelFullyQualifiedName(
                    identifier=datatype.identifier,
                    namespace=tuple(Identifier(segment.as_str) for segment in namespace.names),
                )
                datatype.source_uri = str(file_model.file_path)

    @staticmethod
    def _next_enum_value(value: int | float | bool | str | None) -> int:
        """Apply the legacy implicit enum-value progression."""
        if isinstance(value, int):
            return value + 1
        return 0

    def resolve_local_references(
        self,
        file_model: FIDLFileModel,
    ) -> None:
        """Bind references not resolved from imports during transformation."""
        self._pending_datatype_references = self._import_resolver.resolve_local_references(
            self._pending_datatype_references,
            file_model,
        )

    def _record_datatype_references(self, datatype: DataTypeBase) -> None:
        if isinstance(datatype, TypedefDataType):
            self._record_reference(datatype, datatype.data_type, lambda value: setattr(datatype, "data_type", value))
        elif isinstance(datatype, EnumDataType):
            self._record_reference(datatype, datatype.extends, lambda value: setattr(datatype, "extends", value))
        elif isinstance(datatype, (StructDataType, UnionDataType)):
            self._record_reference(datatype, datatype.extends, lambda value: setattr(datatype, "extends", value))
            for field in datatype.fields:
                self._record_field_references(datatype, field)
        elif isinstance(datatype, ArrayDataType):
            self._record_reference(datatype, datatype.data_type, lambda value: setattr(datatype, "data_type", value))
        elif isinstance(datatype, MapDataType):
            self._record_reference(datatype, datatype.key_type, lambda value: setattr(datatype, "key_type", value))
            self._record_reference(datatype, datatype.value_type, lambda value: setattr(datatype, "value_type", value))

    def _record_field_references(self, datatype: DataTypeBase, field: DataTypeField) -> None:
        if isinstance(field.data_type, ArrayDataType):
            self._record_reference(
                datatype,
                field.data_type.data_type,
                lambda value: setattr(field.data_type, "data_type", value),
            )
        else:
            self._record_reference(datatype, field.data_type, lambda value: setattr(field, "data_type", value))

    def _record_reference(
        self,
        datatype: DataTypeBase,
        reference: object,
        bind: Callable[[DataTypeOrReference], None],
    ) -> None:
        if isinstance(reference, (FullyQualifiedName, Identifier)):
            parser_reference = self._parser_reference_by_model_reference.get(id(reference), reference)
            self._pending_datatype_references_by_declaration.setdefault(id(datatype), []).append(
                PendingDatatypeReference(
                    parser_reference
                    if isinstance(parser_reference, FullyQualifiedName)
                    else self._to_parser_reference(parser_reference),
                    bind,
                    datatype,
                )
            )

    @staticmethod
    @v_args(inline=True)
    def start(model_root: FIDLFileModel) -> FIDLFileModel:
        """Unwrap the grammar's top-level start rule."""
        return model_root

    @v_args(inline=True)
    def fi_model_root(self, package: FullyQualifiedName, *elements: object) -> FIDLFileModel:
        """Build the FIDL file model from its transformed type collections."""
        type_collections: list[TypeCollection] = []
        used_valid_ids: set[str] = set()
        for element in elements:
            if not isinstance(element, TypeCollection):
                continue
            if element.name is not None:
                collection_name = element.name.as_str
                # Match franca2arxml validation for named tc/interface declarations.
                if collection_name in used_valid_ids:
                    raise ValueError(
                        f"Duplicate TypeCollection ID {collection_name} found in "
                        f"{self._transformation_context.file_path}"
                    )
                used_valid_ids.add(collection_name)
            type_collections.append(element)
        # TODO: verify interface names in used_valid_ids set.
        file_model = FIDLFileModel(
            file_path=self._transformation_context.file_path,
            namespace=package,
            imported_files=self._transformation_context.imported_files,
            type_collections=type_collections,
        )
        self.resolve_local_references(file_model)
        return file_model

    @staticmethod
    @v_args(inline=True)
    def fi_model_elements(element: object) -> object:
        """Unwrap top-level FIDL model elements."""
        return element

    @v_args(inline=True)
    def fi_type_collection(self, *elements: object) -> TypeCollection:
        """Collect datatype declarations owned by one FIDL type collection."""
        collection = TypeCollection(name=None)
        for element in elements:
            if isinstance(element, ValidIdentifier):
                collection.name = element
            elif isinstance(element, DataTypeBase):
                collection.datatypes.append(element)
                for pending in self._pending_datatype_references_by_declaration.pop(id(element), []):
                    pending.owning_collection = collection
                    self._pending_datatype_references.append(pending)
        return collection

    @v_args(inline=True)
    def fi_type(self, datatype: DataTypeBase) -> DataTypeBase:
        """Unwrap one FIDL datatype declaration."""
        if isinstance(datatype, PrimitiveDataType):
            raise ValueError(
                "Bare FIDL primitive datatype declarations are not supported "
                f"in {self._transformation_context.file_path}"
            )
        return datatype

    @staticmethod
    @v_args(inline=True)
    def builtin(data_type: PrimitiveDataType) -> PrimitiveDataType:
        """Unwrap a FIDL primitive type reference."""
        return data_type

    @v_args(inline=True)
    def imported(self, reference: FullyQualifiedName) -> FullyQualifiedName | DataTypeBase:
        """Resolve a reference from already transformed imports when possible."""
        return self._import_resolver.resolve_imports(reference, self._transformation_context) or reference

    @v_args(inline=True)
    def interval(self, _interval: object) -> object:
        """Reject unsupported FIDL integer interval types."""
        raise ValueError(f"FIDL Integer intervals are not supported in {self._transformation_context.file_path}")

    @v_args(inline=True)
    def fi_type_def(self, *elements: object) -> TypedefDataType:
        """Transform a FIDL typedef declaration."""
        name = next(element for element in elements if isinstance(element, ValidIdentifier))
        data_type = next(element for element in elements if isinstance(element, _DATA_TYPE_ELEMENTS))
        datatype = TypedefDataType(
            qualified_name=Identifier(name.as_str),
            source_kind=DataTypeSource.FRANCA,
            data_type=self._to_model_reference(data_type),
        )
        self._record_datatype_references(datatype)
        return datatype

    @v_args(inline=True)
    def fi_enumeration_type(self, *elements: object) -> EnumDataType:
        """Transform a FIDL enum declaration and its implicit values."""
        name = next(element for element in elements if isinstance(element, ValidIdentifier))
        extends = next((element for element in elements if isinstance(element, _DATA_TYPE_ELEMENTS)), None)
        values: list[EnumValue] = []
        next_value = 0
        for element in elements:
            if not isinstance(element, _EnumLiteral):
                continue
            value = next_value if element.value is None else element.value
            next_value = self._next_enum_value(value)
            values.append(EnumValue(identifier=Identifier(element.identifier.as_str), value=value))
        enum = EnumDataType(
            qualified_name=Identifier(name.as_str),
            source_kind=DataTypeSource.FRANCA,
            extends=self._to_model_reference(extends),
            values=tuple(values),
        )
        self._record_datatype_references(enum)
        return enum

    @staticmethod
    @v_args(inline=True)
    def fi_enumerator(name: ValidIdentifier, *elements: object) -> _EnumLiteral:
        """Transform one FIDL enum literal."""
        is_negative = any(isinstance(element, Token) and str(element) == "-" for element in elements)
        value = next((element for element in elements if not isinstance(element, Token)), None)
        if is_negative and isinstance(value, (int, float)):
            value = -value
        return _EnumLiteral(identifier=name, value=value)

    @v_args(inline=True)
    def fi_struct_type(self, *elements: object) -> StructDataType:
        """Transform a FIDL struct declaration."""
        datatype = StructDataType(
            qualified_name=Identifier(
                next(element for element in elements if isinstance(element, ValidIdentifier)).as_str
            ),
            source_kind=DataTypeSource.FRANCA,
            extends=self._to_model_reference(
                next((element for element in elements if isinstance(element, _DATA_TYPE_ELEMENTS)), None)
            ),
            fields=tuple(element for element in elements if isinstance(element, DataTypeField)),
        )
        self._record_datatype_references(datatype)
        return datatype

    @v_args(inline=True)
    def fi_union_type(self, *elements: object) -> UnionDataType:
        """Transform a FIDL union declaration."""
        datatype = UnionDataType(
            qualified_name=Identifier(
                next(element for element in elements if isinstance(element, ValidIdentifier)).as_str
            ),
            source_kind=DataTypeSource.FRANCA,
            extends=self._to_model_reference(
                next((element for element in elements if isinstance(element, _DATA_TYPE_ELEMENTS)), None)
            ),
            fields=tuple(element for element in elements if isinstance(element, DataTypeField)),
        )
        self._record_datatype_references(datatype)
        return datatype

    @v_args(inline=True)
    def fi_array_type(self, *elements: object) -> ArrayDataType:
        """Transform a named FIDL array declaration."""
        name = next(element for element in elements if isinstance(element, ValidIdentifier))
        data_type = next(element for element in elements if isinstance(element, _DATA_TYPE_ELEMENTS))
        dimensions = next((element for element in elements if isinstance(element, tuple)), None)
        dimension_min, dimension_max = dimensions if dimensions is not None else (None, None)
        datatype = ArrayDataType(
            qualified_name=Identifier(name.as_str),
            source_kind=DataTypeSource.FRANCA,
            data_type=self._to_model_reference(data_type),
            dimension_min=dimension_min,
            dimension_max=dimension_max,
        )
        self._record_datatype_references(datatype)
        return datatype

    @v_args(inline=True)
    def fi_map_type(self, *elements: object) -> MapDataType:
        """Transform a FIDL map declaration."""
        name = next(element for element in elements if isinstance(element, ValidIdentifier))
        data_types = [element for element in elements if isinstance(element, _DATA_TYPE_ELEMENTS)]
        key_type, value_type = data_types
        datatype = MapDataType(
            qualified_name=Identifier(name.as_str),
            source_kind=DataTypeSource.FRANCA,
            key_type=self._to_model_reference(key_type),
            value_type=self._to_model_reference(value_type),
        )
        self._record_datatype_references(datatype)
        return datatype

    @staticmethod
    @v_args(inline=True)
    def fi_map_from(data_type: object) -> object:
        """Unwrap the map key type reference."""
        return data_type

    @staticmethod
    @v_args(inline=True)
    def fi_map_to(data_type: object) -> object:
        """Unwrap the map value type reference."""
        return data_type

    @staticmethod
    @v_args(inline=True)
    def fi_field(field: DataTypeField) -> DataTypeField:
        """Unwrap a FIDL field declaration."""
        return field

    @staticmethod
    @v_args(inline=True)
    def fi_plain_field(field: DataTypeField) -> DataTypeField:
        """Unwrap an unannotated FIDL field declaration."""
        return field

    @v_args(inline=True)
    def fi_element_declaration(self, data_type: object, *elements: object) -> DataTypeField:
        """Transform a FIDL struct or union field declaration."""
        field_name = next(element for element in elements if isinstance(element, ValidIdentifier))
        dimensions = next((element for element in elements if isinstance(element, tuple)), None)
        if dimensions is not None:
            dimension_min, dimension_max = dimensions
            data_type = ArrayDataType(
                source_kind=DataTypeSource.FRANCA,
                data_type=self._to_model_reference(data_type),
                is_inline=True,
                dimension_min=dimension_min,
                dimension_max=dimension_max,
            )
        return DataTypeField(identifier=Identifier(field_name.as_str), data_type=self._to_model_reference(data_type))

    @staticmethod
    @v_args(inline=True)
    def fi_array_dimension(*dimensions: tuple[str, int]) -> tuple[int | None, int | None]:
        """Preserve the explicitly provided FIDL array bounds."""
        bounds = dict(dimensions)
        return bounds.get("lower"), bounds.get("upper")

    @staticmethod
    @v_args(inline=True)
    def lower_dim(value: object) -> tuple[str, int]:
        """Transform an explicit lower array dimension bound."""
        return "lower", int(str(value))

    @staticmethod
    @v_args(inline=True)
    def upper_dim(value: object) -> tuple[str, int]:
        """Transform an explicit upper array dimension bound."""
        return "upper", int(str(value))

    @staticmethod
    @v_args(inline=True)
    def integer(value: object) -> int:
        """Transform a decimal, hexadecimal, or binary integer literal."""
        return int(str(value), 0)

    @v_args(inline=True)
    def boolean_type(self) -> PrimitiveDataType:
        """Transform the Boolean primitive type name."""
        return PRIMITIVE_TYPES["boolean"]

    @staticmethod
    @v_args(inline=True)
    def boolean_literal(value: object) -> bool:
        """Transform a Boolean literal."""
        return str(value) == "true"

    @v_args(inline=True)
    def string_type(self) -> PrimitiveDataType:
        """Transform the String primitive type name."""
        return PRIMITIVE_TYPES["string"]

    @staticmethod
    @v_args(inline=True)
    def string_literal(value: object) -> str:
        """Transform a string literal while preserving escape text."""
        return str(value).strip("'\"")

    @v_args(inline=True)
    def float_type(self) -> PrimitiveDataType:
        """Transform the Float primitive type name."""
        return PRIMITIVE_TYPES["float"]

    @staticmethod
    @v_args(inline=True)
    def float_literal(value: object) -> str:
        """Transform a Float literal while preserving its source spelling."""
        return str(value)

    @v_args(inline=True)
    def bytebuffer(self) -> PrimitiveDataType:
        """Transform the ByteBuffer primitive type name."""
        return PRIMITIVE_TYPES["bytebuffer"]

    @v_args(inline=True)
    def double_type(self) -> PrimitiveDataType:
        """Transform the Double primitive type name."""
        return PRIMITIVE_TYPES["double"]

    @staticmethod
    @v_args(inline=True)
    def double_literal(value: object) -> str:
        """Transform a Double literal while preserving its source spelling."""
        return str(value)

    @v_args(inline=True)
    def uint8(self) -> PrimitiveDataType:
        """Transform the UInt8 primitive type name."""
        return PRIMITIVE_TYPES["uint8"]

    @v_args(inline=True)
    def uint16(self) -> PrimitiveDataType:
        """Transform the UInt16 primitive type name."""
        return PRIMITIVE_TYPES["uint16"]

    @v_args(inline=True)
    def uint32(self) -> PrimitiveDataType:
        """Transform the UInt32 primitive type name."""
        return PRIMITIVE_TYPES["uint32"]

    @v_args(inline=True)
    def uint64(self) -> PrimitiveDataType:
        """Transform the UInt64 primitive type name."""
        return PRIMITIVE_TYPES["uint64"]

    @v_args(inline=True)
    def int8(self) -> PrimitiveDataType:
        """Transform the Int8 primitive type name."""
        return PRIMITIVE_TYPES["int8"]

    @v_args(inline=True)
    def int16(self) -> PrimitiveDataType:
        """Transform the Int16 primitive type name."""
        return PRIMITIVE_TYPES["int16"]

    @v_args(inline=True)
    def int32(self) -> PrimitiveDataType:
        """Transform the Int32 primitive type name."""
        return PRIMITIVE_TYPES["int32"]

    @v_args(inline=True)
    def int64(self) -> PrimitiveDataType:
        """Transform the Int64 primitive type name."""
        return PRIMITIVE_TYPES["int64"]
