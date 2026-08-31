"""Name-based URL lookup.

The project addresses its own endpoints by name (``recipe:article-list``)
rather than by literal path, and the routers keep publishing those names.
Colons separated the namespaces before the migration; the router now registers
the same names with dots, so the two spellings are accepted here and the call
sites stay unchanged.
"""
from flask import url_for


def reverse(viewname, args=None, kwargs=None, **extra):
    endpoint = viewname.replace(':', '.')
    values = dict(kwargs or {}, **extra)
    if args:
        # The routes in this project take a single positional argument, so the
        # values line up with the one remaining placeholder in the rule.
        rule = _rule_for(endpoint)
        for name, value in zip(_arguments(rule), args):
            values[name] = value
    return url_for(endpoint, **values)


def _rule_for(endpoint):
    from flask import current_app

    for rule in current_app.url_map.iter_rules(endpoint):
        return rule
    return None


def _arguments(rule):
    if rule is None:
        return ()
    return [name for name in rule.arguments if name != 'format']
