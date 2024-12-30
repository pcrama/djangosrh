from django import template

register = template.Library()

@register.filter
def cents_to_euros(display_value: str) -> str:
    try:
        value = int(display_value)
        euros = abs(value) // 100
        cents = abs(value) % 100
        sign = "" if value >= 0 else "-"
        return f"{sign}{euros}.{cents:02d}€"
    except (TypeError, ValueError) as e:
        return ""
