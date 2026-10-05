from __future__ import annotations

from factories import OptionalResourceFactory, ResourceFactory
from fuzzy import Fuzzy
from test_app.rest import OptionalResourceSerializer, ResourceSerializer


def test_serializer_representation() -> None:
    """A stored file is represented by its URL, from the storage."""
    resource = ResourceFactory.build(blob="key/file.txt")
    serializer = ResourceSerializer(resource)

    assert serializer.data["blob"] == Fuzzy(r"^https?://.*/key/file\.txt")


def test_serializer_representation_empty() -> None:
    """An empty optional field is represented as null."""
    resource = OptionalResourceFactory.build(blob="")
    serializer = OptionalResourceSerializer(resource)

    assert serializer.data["blob"] is None
