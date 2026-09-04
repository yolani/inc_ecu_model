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

# UUID Reference Rationale

UUID references are a reasonable design for a serializable, graph-shaped model.
Pydantic primarily models trees; it does not preserve object identity or graph
edges as part of a JSON model contract.

## Revalidation Can Replace Nested Model Instances

```python
from pydantic import BaseModel, ConfigDict


class Field(BaseModel):
    identifier: str


class Struct(BaseModel):
    model_config = ConfigDict(revalidate_instances="always")
    fields: list[Field]


original = Field(identifier="x")
struct = Struct(fields=[original])

assert struct.fields[0] is not original  # Object identity is not a contract.
```

If another part of the builder also retains `original`, it can then operate on
an instance that is no longer part of the final model tree.

## Containers Are Recreated Too

```python
fields = [Field(identifier="x")]
struct = Struct(fields=fields)

assert struct.fields is not fields
```

This is normal validation behavior. However, it means a direct reference to an
instance within such a container is not a stable graph link.

## Direct Cross-References Become Copies After JSON Round-Trips

```python
from pydantic import BaseModel


class DataType(BaseModel):
    identifier: str


class Member(BaseModel):
    data_type: DataType


position = DataType(identifier="Position")
member = Member(data_type=position)

restored = Member.model_validate_json(member.model_dump_json())

assert restored.data_type == position
assert restored.data_type is not position
```

After deserialization, two equivalent `DataType` instances exist. Mutating one
does not affect the other.

```python
position.identifier = "PositionV2"

assert restored.data_type.identifier == "Position"
```

With UUID references, resolving after restoring the registry always returns the
canonical node.

## Reusing an Instance Does Not Create a Shared JSON Node

```python
class Message(BaseModel):
    first: DataType
    second: DataType


position = DataType(identifier="Position")
message = Message(first=position, second=position)

payload = message.model_dump()
restored = Message.model_validate(payload)

assert restored.first is not restored.second
```

The JSON payload contains two embedded copies of `Position`, not one node with
two edges. A `target_id` representation makes those edges explicit.

```json
{
  "first": {"target_id": "..."},
  "second": {"target_id": "..."}
}
```

The definition itself is stored once in the registry.

## Cycles Cannot Be Serialized as Nested Models

```python
class TypeAlias(BaseModel):
    identifier: str
    target: "TypeAlias | None" = None


TypeAlias.model_rebuild()

first = TypeAlias(identifier="First")
second = TypeAlias(identifier="Second")
first.target = second
second.target = first

first.model_dump_json()  # PydanticSerializationError: circular reference detected
```

Data type cycles may be prohibited by domain validation later. A UUID graph can
still represent and detect them deliberately. A nested model tree fails first
at the serialization level.

## Pickle Preserves Identity, but Is Not an Interchangeable Model Format

```python
import pickle


position = DataType(identifier="Position")
message = Message(first=position, second=position)

restored = pickle.loads(pickle.dumps(message))

assert restored.first is restored.second
```

This works inside one Pickle object graph. It does not make object identity part
of the `model_dump()` or JSON contract, does not preserve context when only a
submodel is serialized, and does not solve forward references. Consumers must
also retain the complete object graph for direct Python references to remain
valid.

For a Bazel cache, pickling the registry is appropriate: one payload contains
all canonical elements, `ModelRegistry.deserialize()` restores them centrally,
and every `ModelRef(target_id=...)` remains valid even when Pydantic recreates
instances during validation.

## Builder API

The builder writes and reads normal members. The model stores UUIDs internally.

```python
field = DataTypeField(
    identifier="position",
    data_type=position_type,
)

message = StructDataType(
    identifier="Message",
    source_kind=DataTypeSource.FRANCA,
    fields=[field],
)

assert message.fields[0].identifier == "position"
```

Internally, `message.fields[0]` stores a UUID-backed `ModelRef`. Its attribute
access resolves transparently, so builder and consumer code normally neither
uses `target_id` nor calls `resolve()`.

## Operational Constraint

`ModelRegistry` is global process state. Builders and tests must create models
with a fresh registry or explicitly save and restore the registry state.
