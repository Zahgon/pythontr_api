import unittest

from app.api import filters

from core.models import Category, get_user_model


def test_user(email='filter@hotmail.com', password='123qwe'):
    return get_user_model().objects.create_user(email, password)


class FakeRequest(object):

    def __init__(self, **params):
        self.query_params = params


class FakeView(object):

    def __init__(self, model=None, search_fields=None, filterset_fields=None):
        self.model = model
        if search_fields is not None:
            self.search_fields = search_fields
        if filterset_fields is not None:
            self.filterset_fields = filterset_fields


class BaseFilterBackendTests(unittest.TestCase):

    def test_filter_queryset_must_be_overridden(self):
        backend = filters.BaseFilterBackend()

        with self.assertRaises(NotImplementedError):
            backend.filter_queryset(
                FakeRequest(), Category.query, FakeView(Category)
            )


class IsBooleanTests(unittest.TestCase):

    def test_boolean_column(self):
        user = get_user_model()

        self.assertTrue(filters._is_boolean(user.is_active))

    def test_string_column(self):
        user = get_user_model()

        self.assertFalse(filters._is_boolean(user.email))


class SearchFilterTests(unittest.TestCase):

    def setUp(self):
        self.user = test_user()
        self.backend = filters.SearchFilter()
        self.view = FakeView(Category, search_fields=['name', 'short_name'])
        Category.objects.create(
            user=self.user,
            name='Ruby programlama',
            title='Ruby',
            short_name='ruby',
        )
        Category.objects.create(
            user=self.user,
            name='Elixir programlama',
            title='Elixir',
            short_name='elixir',
        )

    def filter(self, **params):
        return self.backend.filter_queryset(
            FakeRequest(**params), Category.query, self.view
        ).all()

    def test_search_terms_split_on_whitespace(self):
        request = FakeRequest(search='ruby elixir')

        self.assertEqual(
            self.backend.get_search_terms(request), ['ruby', 'elixir']
        )

    def test_search_terms_split_on_commas(self):
        request = FakeRequest(search='ruby,elixir')

        self.assertEqual(
            self.backend.get_search_terms(request), ['ruby', 'elixir']
        )

    def test_search_terms_strip_null_bytes(self):
        request = FakeRequest(search='ru\x00by')

        self.assertEqual(self.backend.get_search_terms(request), ['ruby'])

    def test_search_terms_empty_without_the_parameter(self):
        self.assertEqual(self.backend.get_search_terms(FakeRequest()), [])

    def test_search_fields_read_from_the_view(self):
        self.assertEqual(
            self.backend.get_search_fields(self.view), ['name', 'short_name']
        )

    def test_search_fields_default_to_nothing(self):
        self.assertIsNone(self.backend.get_search_fields(FakeView(Category)))

    def test_match_is_case_insensitive(self):
        names = [category.name for category in self.filter(search='RUBY')]

        self.assertEqual(names, ['Ruby programlama'])

    def test_match_is_partial(self):
        names = sorted(
            category.name for category in self.filter(search='programlama')
        )

        self.assertEqual(names, [
            'Elixir programlama',
            'Mobil Programlama',
            'Programlama',
            'Ruby programlama',
        ])

    def test_second_field_is_searched(self):
        names = [category.name for category in self.filter(search='elixir')]

        self.assertEqual(names, ['Elixir programlama'])

    def test_every_term_must_match(self):
        self.assertEqual(self.filter(search='ruby elixir'), [])

    def test_without_the_parameter_nothing_is_filtered(self):
        self.assertEqual(len(self.filter()), Category.query.count())

    def test_without_search_fields_nothing_is_filtered(self):
        queryset = self.backend.filter_queryset(
            FakeRequest(search='ruby'), Category.query, FakeView(Category)
        )

        self.assertEqual(queryset.count(), Category.query.count())


class FieldFilterBackendTests(unittest.TestCase):

    def setUp(self):
        self.backend = filters.FieldFilterBackend()
        self.view = FakeView(
            get_user_model(), filterset_fields=['is_active', 'is_staff']
        )
        self.model = get_user_model()
        self.active = get_user_model().objects.create_user(
            'active@hotmail.com', '123qwe'
        )
        self.active.is_active = True
        self.active.save()
        self.inactive = get_user_model().objects.create_user(
            'inactive@hotmail.com', '123qwe'
        )

    def filter(self, **params):
        return self.backend.filter_queryset(
            FakeRequest(**params), self.model.query, self.view
        ).all()

    def test_filterset_fields_read_from_the_view(self):
        self.assertEqual(
            self.backend.get_filterset_fields(self.view),
            ['is_active', 'is_staff'],
        )

    def test_filterset_fields_default_to_nothing(self):
        view = FakeView(get_user_model())
        self.assertEqual(self.backend.get_filterset_fields(view), [])

    def test_true_matches(self):
        emails = [user.email for user in self.filter(is_active='true')]

        self.assertEqual(emails, ['active@hotmail.com'])

    def test_false_matches(self):
        emails = [user.email for user in self.filter(is_active='false')]

        self.assertEqual(emails, ['inactive@hotmail.com'])

    def test_one_and_zero_are_accepted(self):
        self.assertEqual(len(self.filter(is_active='1')), 1)
        self.assertEqual(len(self.filter(is_active='0')), 1)

    def test_unparsable_boolean_matches_nothing(self):
        self.assertEqual(self.filter(is_active='maybe'), [])

    def test_absent_parameters_are_skipped(self):
        self.assertEqual(len(self.filter()), self.model.query.count())

    def test_two_fields_are_combined(self):
        self.assertEqual(
            self.filter(is_active='true', is_staff='true'), []
        )

    def test_non_boolean_column_compares_the_raw_value(self):
        view = FakeView(get_user_model(), filterset_fields=['email'])
        queryset = self.backend.filter_queryset(
            FakeRequest(email='active@hotmail.com'), self.model.query, view
        )

        self.assertEqual(
            [user.email for user in queryset], ['active@hotmail.com']
        )
