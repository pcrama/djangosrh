from datetime import date
from typing import Sequence
from django import template

from core import banking

register = template.Library()

register.filter("cents_to_euros", banking.cents_to_euros)


@register.filter
def plural(count: int, name_and_plural: str|Sequence[str]) -> str:
    """Pluralize string based on the given count.
    
    Usage in templates:
        {{ count|plural:"word,words" }}
    
    :param count: The count of items.
    :param name_and_plural: A comma-separated string with singular and plural forms
                            (e.g., "word,words") or a sequence of 2 strings.
    :return: A string with the appropriate singular or plural form.
    """
    if isinstance(name_and_plural, str):
        # Split the input into singular and plural parts
        name_and_plural = name_and_plural.split(',')
        if len(name_and_plural) == 1:
            name_and_plural = (name_and_plural[0], f"{name_and_plural[0]}s")

    if len(name_and_plural) != 2:
        raise ValueError('nom_et_pluriel must contain singular and plural forms separated by a comma.')
    
    singular, plural = name_and_plural
    return f'1 {singular}' if count == 1 else f'{count} {plural}'


register.filter("format_bank_id", banking.format_bank_id)


@register.filter
def french_date(d: date) -> str:
    return d.strftime("%d/%m/%Y")
