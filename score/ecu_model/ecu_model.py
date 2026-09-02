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
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class EcuModel(BaseModel):
    """
    This class provides a registry for instances of EcuModelElement. All objects of type EcuModelElement are
    automatically tracked in the registry to ensure uniqueness and to make them resolvable by their identifier for the
    whole lifetime of the process.
    Future extensions, additional post-initialization, validation, etc. actions can be implemented here.
    """

    model_registry: ClassVar[dict[UUID, "EcuModelElement"]] = {}

    def model_post_init(self, context: Any, /) -> None:
        """
        Post-initialization hook for the model. Overwrite of BaseModel.model_post_init() method.

        This method is called after the model is instantiated and all field validators are applied.

        Args:
            context: Additional context for post-initialization actions.

        Raises:
            TypeError: If the instance is neither the root EcuModel nor an EcuModelElement.
            ValueError: If an instance with the same ID already exists in the registry.
        """
        if type(self) is EcuModel:
            # The root object of a model is not itself tracked in the registry.
            return
        if not isinstance(self, EcuModelElement):
            raise TypeError(f"Expected instance of EcuModelElement, got {type(self).__name__}")
        if self.id in EcuModel.model_registry.keys():
            raise ValueError(f"Duplicate instance {str(self)}")
        EcuModel.model_registry[self.id] = self

    @classmethod
    def serialize(cls) -> bytes:
        """
        Pickle the whole model registry, i.e. every registered EcuModelElement.
        """
        return pickle.dumps(EcuModel.model_registry, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def deserialize(cls, data: bytes) -> int:
        """
        Replace the model registry with a previously serialized one and return the number of restored elements.

        Args:
            data: Payload produced by serialize().

        Raises:
            TypeError: If the payload does not contain a registry of model elements.
        """
        restored = pickle.loads(data)
        if not isinstance(restored, dict) or not all(
            isinstance(key, UUID) and isinstance(value, EcuModelElement) for key, value in restored.items()
        ):
            raise TypeError("Payload does not contain an EcuModel registry")
        # Replacing the contents rather than the dict itself keeps existing references to the registry valid.
        EcuModel.model_registry.clear()
        EcuModel.model_registry.update(restored)
        return len(EcuModel.model_registry)


class EcuModelElement(EcuModel):
    """
    Base class to be used by all objects tracked in the EcuModel.model_registry.
    """

    """
    Basic configuration for the model element.
    Set strict validation for the model fields, so that the model is re-validated whenever accessed or modified.
    See https://pydantic.dev/docs/validation/dev/api/pydantic/config/ for more details.
    """
    model_config = ConfigDict(
        revalidate_instances="always",
        validate_assignment=True,
    )

    """
    Properties of the model element.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique identifier of the model element")
    description: str = Field(default="", description="Human-readable description of the model element")

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, description={self.description})"
