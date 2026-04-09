from django import template

register = template.Library()

@register.filter(name='split_creds')
def split_creds(value):
    """
    Splits a credentials string formatted as 'login|password'
    """
    if not value or '|' not in value:
        return ['', '']
    return value.split('|')
