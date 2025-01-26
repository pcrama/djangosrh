from datetime import date
from typing import Sequence
from django import template

register = template.Library()

@register.filter
def cents_to_euros(display_value: str|int, unit="€") -> str:
    try:
        value = int(display_value)
        euros = abs(value) // 100
        cents = abs(value) % 100
        sign = "" if value >= 0 else "-"
        return f"{sign}{euros}.{cents:02d}{unit}"
    except (TypeError, ValueError):
        return ""


@register.filter
def plural(count: int, name_and_plural: str|Sequence[str]):
    """Pluralize string based on the given count.
    
    Usage in templates:
        {{ count|pluriel_naif:"word,words" }}
    
    :param nombre: The count of items.
    :param nom_et_pluriel: A comma-separated string with singular and plural forms 
                           (e.g., "word,words").
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


@register.filter
def format_bank_id(x: str) -> str:
    bank_id = ''.join(c for c in x if c.isdigit())
    if len(bank_id) != 12:
        return x
    return f'+++{bank_id[0:3]}/{bank_id[3:7]}/{bank_id[7:12]}+++'


@register.filter
def french_date(d: date) -> str:
    return d.strftime("%d/%m/%Y")
