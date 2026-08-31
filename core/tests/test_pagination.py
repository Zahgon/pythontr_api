import unittest

from flask import current_app, request

from app.api import pagination
from app.api.exceptions import NotFound

from core.models import Category
from core.pagination import CustomPagination


LIST_URL = '/api/recipe/categories/'


class QueryParamTests(unittest.TestCase):

    def test_replace_query_param(self):
        url = 'http://testserver/api/recipe/categories/?page=2'
        replaced = pagination.replace_query_param(url, 'page', 5)

        self.assertEqual(
            replaced, 'http://testserver/api/recipe/categories/?page=5'
        )

    def test_replace_query_param_adds_missing_key(self):
        url = 'http://testserver/api/recipe/categories/'
        replaced = pagination.replace_query_param(url, 'page', 3)

        self.assertEqual(
            replaced, 'http://testserver/api/recipe/categories/?page=3'
        )

    def test_remove_query_param(self):
        url = 'http://testserver/api/recipe/categories/?page=2&search=py'
        removed = pagination.remove_query_param(url, 'page')

        self.assertEqual(
            removed, 'http://testserver/api/recipe/categories/?search=py'
        )

    def test_remove_query_param_keeps_other_keys(self):
        url = 'http://testserver/api/recipe/categories/?search=py'
        removed = pagination.remove_query_param(url, 'page')

        self.assertEqual(
            removed, 'http://testserver/api/recipe/categories/?search=py'
        )


class PaginatorTests(unittest.TestCase):

    def test_count_of_a_list(self):
        paginator = pagination.Paginator(list(range(17)), 5)

        self.assertEqual(paginator.count, 17)
        self.assertEqual(paginator.num_pages, 4)

    def test_count_of_a_queryset(self):
        paginator = pagination.Paginator(Category.query, 5)

        self.assertEqual(paginator.count, 17)
        self.assertEqual(paginator.num_pages, 4)

    def test_empty_list_still_has_one_page(self):
        paginator = pagination.Paginator([], 5)

        self.assertEqual(paginator.count, 0)
        self.assertEqual(paginator.num_pages, 1)

    def test_validate_number_rejects_a_non_number(self):
        paginator = pagination.Paginator(list(range(17)), 5)

        with self.assertRaises(pagination.InvalidPage):
            paginator.validate_number('nope')

    def test_validate_number_rejects_a_number_below_one(self):
        paginator = pagination.Paginator(list(range(17)), 5)

        with self.assertRaises(pagination.InvalidPage):
            paginator.validate_number(0)

    def test_validate_number_rejects_a_number_past_the_end(self):
        paginator = pagination.Paginator(list(range(17)), 5)

        with self.assertRaises(pagination.InvalidPage):
            paginator.validate_number(5)

    def test_page_slices_the_object_list(self):
        paginator = pagination.Paginator(list(range(17)), 5)
        page = paginator.page(2)

        self.assertEqual(list(page), [5, 6, 7, 8, 9])
        self.assertEqual(len(page), 5)
        self.assertEqual(page[0], 5)

    def test_last_page_is_short(self):
        paginator = pagination.Paginator(list(range(17)), 5)
        page = paginator.page(4)

        self.assertEqual(list(page), [15, 16])

    def test_first_page_links(self):
        paginator = pagination.Paginator(list(range(17)), 5)
        page = paginator.page(1)

        self.assertTrue(page.has_next())
        self.assertFalse(page.has_previous())
        self.assertEqual(page.next_page_number(), 2)

    def test_last_page_links(self):
        paginator = pagination.Paginator(list(range(17)), 5)
        page = paginator.page(4)

        self.assertFalse(page.has_next())
        self.assertTrue(page.has_previous())
        self.assertEqual(page.previous_page_number(), 3)


class PageNumberPaginationTests(unittest.TestCase):

    def paginate(self, query_string=''):
        paginator = CustomPagination()
        context = current_app.test_request_context(
            '{}{}'.format(LIST_URL, query_string)
        )
        context.push()
        try:
            page = paginator.paginate_queryset(Category.query, request)
            response = paginator.get_paginated_response(page)
        finally:
            context.pop()
        return paginator, page, response.data

    def test_page_size_comes_from_the_configuration(self):
        paginator = CustomPagination()
        context = current_app.test_request_context(LIST_URL)
        context.push()
        try:
            size = paginator.get_page_size(request)
        finally:
            context.pop()

        self.assertEqual(size, current_app.config['PAGE_SIZE'])

    def test_first_page_envelope(self):
        current_app.config['PAGE_SIZE'] = 5
        try:
            paginator, page, data = self.paginate()
        finally:
            current_app.config['PAGE_SIZE'] = 27

        self.assertEqual(len(page), 5)
        self.assertEqual(
            list(data.keys()),
            [
                'count',
                'first_page',
                'last_page',
                'next',
                'previous',
                'last_page_number',
                'current_page',
                'results',
            ],
        )
        self.assertEqual(data['count'], 17)
        self.assertEqual(data['current_page'], 1)
        self.assertEqual(data['last_page_number'], 4)
        self.assertEqual(data['previous'], None)
        self.assertEqual(data['next'], '{}?page=2'.format(LIST_URL))

    def test_middle_page_envelope_carries_both_links(self):
        current_app.config['PAGE_SIZE'] = 5
        try:
            paginator, page, data = self.paginate('?page=2')
        finally:
            current_app.config['PAGE_SIZE'] = 27

        self.assertEqual(data['current_page'], 2)
        self.assertEqual(data['next'], '{}?page=3'.format(LIST_URL))
        self.assertEqual(data['previous'], LIST_URL)
        self.assertEqual(data['first_page'], LIST_URL)
        self.assertEqual(data['last_page'], '{}?page=4'.format(LIST_URL))

    def test_last_page_keyword_selects_the_final_page(self):
        current_app.config['PAGE_SIZE'] = 5
        try:
            paginator, page, data = self.paginate('?page=last')
        finally:
            current_app.config['PAGE_SIZE'] = 27

        self.assertEqual(data['current_page'], 4)
        self.assertEqual(len(page), 2)
        self.assertEqual(data['next'], None)

    def test_a_page_past_the_end_is_not_found(self):
        current_app.config['PAGE_SIZE'] = 5
        paginator = CustomPagination()
        context = current_app.test_request_context(
            '{}?page=99'.format(LIST_URL)
        )
        context.push()
        try:
            with self.assertRaises(NotFound):
                paginator.paginate_queryset(Category.query, request)
        finally:
            context.pop()
            current_app.config['PAGE_SIZE'] = 27
