from django.test import Client
import pytest


@pytest.mark.django_db()
def test_ninja_serializer_data_invalid(client: Client) -> None:
    response = client.post(
        "/api/ninja/resources/",
        data={"blob": "invalid_key"},
        content_type="application/json",
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "value_error",
                "loc": ["body", "data", "blob"],
                "msg": "Value error, Invalid S3 file field value",
                "ctx": {"error": "Invalid S3 file field value"},
            }
        ]
    }


@pytest.mark.django_db()
def test_ninja_serializer_is_valid(client: Client, s3ff_field_value: str) -> None:
    response = client.post(
        "/api/ninja/resources/",
        data={"blob": s3ff_field_value},
        content_type="application/json",
    )
    assert response.status_code == 201
    assert response.json()["blob"].startswith("http://localhost:9000/s3ff-test/test_key")
