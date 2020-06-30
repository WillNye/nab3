import re


def camel_to_snake(str_obj):
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', str_obj).lower()
