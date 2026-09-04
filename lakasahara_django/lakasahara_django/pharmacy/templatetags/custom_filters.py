from django import template

register = template.Library()


@register.filter
def split(value, separator):
    """Split a string by a separator."""
    if not value:
        return []
    return value.split(separator)
