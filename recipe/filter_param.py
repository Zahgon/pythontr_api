"""Query-parameter filter rules.

A rule is active when its ``check`` argument is not ``None``. An EMPTY string is not
``None``, so ``?search=`` and ``?me=`` are both active rules -- and so is the category
rule, whose ``check`` is a list that is empty rather than absent.
"""


class FilterParam:

    def __init__(self, check, **kwargs):
        self.check = True if check is not None else False
        self.params = {k: v for k, v in kwargs.items() if v is not None}

    def is_check(self):
        return self.check

    def get_param(self):
        return self.params


class Search(FilterParam):
    pass


class Category(FilterParam):
    pass


class Me(FilterParam):
    pass


class Inbox(FilterParam):
    pass


class Outbox(FilterParam):
    pass


class RulesFilter:

    def __init__(self, rules):
        self.rules = rules

    def get_res(self):
        for rule in self.rules:
            if rule.is_check():
                yield rule
