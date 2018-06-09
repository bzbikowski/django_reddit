from django.template.defaulttags import register


@register.filter
def get_item(dictionary, key):
    """
    Needed because there's no built in .get in django templates
    when working with dictionaries.
    :param dictionary: python dictionary
    :param key: valid dictionary key type
    :return: value of that key or None
    """
    return dictionary.get(key)
