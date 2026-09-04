<!----
*******************************************************************************
Copyright (c) 2026 Contributors to the Eclipse Foundation

See the NOTICE file(s) distributed with this work for additional
information regarding copyright ownership.

This program and the accompanying materials are made available under the
terms of the Apache License Version 2.0 which is available at
https://www.apache.org/licenses/LICENSE-2.0

SPDX-License-Identifier: Apache-2.0
*******************************************************************************
-->

# Orion Builder Migration

This guide migrates a builder that produces Orion's
`nautilus...data_type_definition` models to `score.ecu_model`.

## Core Change

The Orion builder represents declared data types as an object tree and links
objects through either direct instances or `BaseQualifiedName`. The SCORE model
registers each declared element under a UUID. References store only that UUID,
but can be read and assigned like the referenced element.

Create model elements before creating the model objects that contain references
to them. Pass elements directly at construction sites; `ModelRef` and
`DataTypeRef` convert them to UUID references automatically.

```python
from score.ecu_model.data_types.common import DataTypeSource
from score.ecu_model.data_types.composite import DataTypeField
from score.ecu_model.data_types.primitives import PrimitiveDataType
from score.ecu_model.data_types.struct import StructDataType

field = DataTypeField(identifier="x", data_type=PrimitiveDataType.FLOAT)
position = StructDataType(
    identifier="Position",
    namespace="app.geometry",
    source_kind=DataTypeSource.FRANCA,
    fields=[field],
)

assert position.fields[0].identifier == "x"
```

The stored value of `position.fields[0]` is a `ModelRef`. `target_id` remains
available for serialization and diagnostics; builder code should normally not
need it or call `resolve()`.

## Type Mapping

| Orion | SCORE | Migration |
|---|---|---|
| `DataTypeModel` | `DataTypeBase` | Abstract base in both models; do not instantiate. |
| `PrimitiveDataType(primitive=...)` | `PrimitiveDataType` enum member | Convert `old.primitive` directly. Do not emit a declared model element. |
| `ExternalDataType` | `ExternalDataType` | Map common metadata and `header`; drop `bazel_target`. |
| `EnumDataType` | `EnumDataType` | Create `EnumValue` elements first, then pass them as `values`. |
| `EnumValue` | `EnumValue` | `name` becomes `identifier`; it is now registered and has `id` and `description`. |
| `StructDataType` | `StructDataType` | Create `DataTypeField` elements first, then pass them as `fields`. |
| `UnionDataType` | `UnionDataType` | Same as struct; SCORE rejects `optional=True` fields. |
| `DataTypeField` | `DataTypeField` | `name` becomes `identifier`; it is now registered and has `id`. |
| `ArrayDataType` | `ArrayDataType` | `name` becomes `identifier`; otherwise map fields unchanged. |
| `MapDataType` | `MapDataType` | `map_from` becomes `key_type`; `map_to` becomes `value_type`. |
| `TypedefDataType` | `TypedefDataType` | Map `data_type` unchanged. |

## Metadata Mapping

| Orion field | SCORE field | Required action |
|---|---|---|
| `name` | `identifier` | Rename. Values must obey source-language identifier rules. |
| `namespace` | `namespace` | Convert `BaseQualifiedName` to a string using the selected source-language separator. Do not use Orion's unconditional `::` key format. |
| `source_kind: str | None` | `source_kind: DataTypeSource` | Required for every declared type. Map `"franca"`, `"protobuf"`, and `"cpp_header_file"` to the enum. |
| `source_uri` | `source_uri` | Keep string; SCORE rejects empty and NUL-containing values. |
| `description` | `description` | Unchanged. |
| `deployment_properties` | `deployment_properties` | Unchanged. |
| `data_type_key` | `fully_qualified_name` | Use SCORE's property. It uses source-language separators. |
| `bazel_target` | none | Drop; build dependency validation belongs to BUILD-level tooling. |

`ExternalDataType.header` is a Pydantic `FilePath`, so the builder must provide
a path to an existing regular file, not a C++ include spelling such as
`"<foo/bar.hpp>"`.

## Reference Conversion

Replace each Orion `BaseQualifiedName | DataTypeDefinition` link with a SCORE
`DataTypeRef`. For normal construction, pass the target element directly:

```python
alias = TypedefDataType(
    identifier="PositionAlias",
    source_kind=DataTypeSource.FRANCA,
    data_type=position,
)

map_type = MapDataType(
    identifier="PositionsById",
    source_kind=DataTypeSource.FRANCA,
    key_type=PrimitiveDataType.UINT32,
    value_type=position,
)
```

A qualified-name link from the old builder needs a lookup phase. Resolve it to
exactly one declared SCORE data type, then pass that element. For genuinely
forward references, allocate a UUID for every declaration during a first pass
and create `DataTypeRef(target_id=declared_id)`. The target can register later.

Use `DataTypeRef` only for declared data types. Use `ModelRef` for
`DataTypeField` and `EnumValue` references. Usually neither wrapper needs to be
constructed explicitly because direct elements are accepted.

## Builder Order

1. Convert every Orion primitive object to its `PrimitiveDataType` enum member.
2. Convert names and namespaces; validate that every declared type has a known
   `DataTypeSource`.
3. Create `EnumValue` and `DataTypeField` elements. They register immediately.
4. Create declared types, passing known targets directly and UUID references for
   unresolved forward targets.
5. Resolve old qualified-name links against the builder's declaration index;
   report missing or ambiguous names before model construction completes.
6. Serialize cache data with `ModelRegistry.serialize()`. Restore it with
   `ModelRegistry.deserialize()` before consumers inspect references.

For model construction, enum values and composite fields are validated and
resolved immediately. They must therefore exist before their containing enum,
struct, or union is built. A declared type used as a field's `data_type` may be
a forward UUID reference because that particular link is resolved lazily.

## Validation Differences

- SCORE source kind is mandatory and determines valid identifier/namespace syntax.
- Inline arrays require `is_inline=True`, `identifier=None`, and `namespace=None`.
  Named arrays require `is_inline=False` and an identifier.
- Enum values and field numbers must be either all explicit or all omitted;
  explicit values must be unique.
- Struct and union field identifiers must be unique; explicit field numbers must
  be unique.
- `extends` is allowed only for Franca and must refer to the same data-type kind.
- UUIDs must be unique across all registered elements. Do not clone elements
  with an existing `id`.

## Suggested Adapter Boundary

Keep Orion imports and qualified-name resolution inside one adapter module. Its
public output should be only SCORE model elements and `ModelRegistry` cache
bytes. This keeps the builder free of SCORE UUID details while avoiding a
partial migration where both reference systems escape into downstream tools.
