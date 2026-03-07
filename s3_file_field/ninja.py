from typing import Annotated, Any

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from s3_file_field.widgets import S3PlaceholderFile


class _S3FileFieldValueTypeMetadata:
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        def validate_from_str(value: str) -> S3PlaceholderFile:
            file_obj = S3PlaceholderFile.from_field(value)
            if file_obj is None:
                raise ValueError("Invalid S3 file field value")
            return file_obj

        from_str_schema = core_schema.no_info_before_validator_function(
            validate_from_str,
            schema=core_schema.is_instance_schema(S3PlaceholderFile),
        )

        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=from_str_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: str(instance)
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(core_schema.str_schema())


S3FileFieldValue = Annotated[S3PlaceholderFile, _S3FileFieldValueTypeMetadata]
