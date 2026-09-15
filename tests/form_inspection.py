from __future__ import annotations

from typing import TYPE_CHECKING

from django.test.html import parse_html

if TYPE_CHECKING:
    from django.forms import BaseForm, BoundField

# The element's own boolean attributes, which parse_html doesn't know to normalize
ELEMENT_BOOLEAN_ATTRIBUTES = {"cleared"}


def rendered_attrs(bound_field: BoundField) -> dict[str, str | None]:
    """Return the attributes of the "s3-file-input" element rendered by a bound field."""
    element = parse_html(str(bound_field))
    assert element.name == "s3-file-input"
    attrs = dict(element.attributes)
    # Boolean attributes (like "required") have a value of None; apply the same normalization
    # as parse_html to the element's own
    for name in ELEMENT_BOOLEAN_ATTRIBUTES:
        if name in attrs and (not attrs[name] or attrs[name] == name):
            attrs[name] = None
    return attrs


def field_error_codes(form: BaseForm, field_name: str) -> list[str | None]:
    """Return the error codes for one field of a bound form, in order."""
    return [error.code for error in form.errors.as_data().get(field_name, [])]
