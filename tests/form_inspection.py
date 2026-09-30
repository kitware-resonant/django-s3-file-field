from __future__ import annotations

from typing import TYPE_CHECKING

from django.test.html import parse_html

if TYPE_CHECKING:
    from django.forms import BaseForm, BoundField


def rendered_attrs(bound_field: BoundField) -> dict[str, str | None]:
    """Return the attributes of the "s3-file-input" element rendered by a bound field."""
    element = parse_html(str(bound_field))
    assert element.name == "s3-file-input"
    # Boolean attributes (like "required") have a value of None
    return dict(element.attributes)


def field_error_codes(form: BaseForm, field_name: str) -> list[str | None]:
    """Return the error codes for one field of a bound form, in order."""
    return [error.code for error in form.errors.as_data().get(field_name, [])]
