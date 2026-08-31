import unittest

from core import aggregates
from core.exceptions import FieldError
from core.models import PageVisit, get_user_model


def test_user(email='aggregate@hotmail.com', password='123qwe'):
    return get_user_model().objects.create_user(email, password)


def visit(user, path, device_type, ip_address, hour=9, browser='Chrome'):
    created = PageVisit(
        user=user,
        path=path,
        device_type=device_type,
        ip_address=ip_address,
        browser=browser,
        method='GET',
    )
    created.save()
    created.timestamp = created.timestamp.replace(hour=hour)
    return created.save()


class AggregateTests(unittest.TestCase):

    def test_count_expression_names_the_column(self):
        expression = aggregates.Count('id').expression(PageVisit)

        self.assertIn('count', str(expression).lower())
        self.assertIn('id', str(expression).lower())

    def test_count_distinct_expression(self):
        expression = aggregates.Count('ip_address', distinct=True)

        rendered = str(expression.expression(PageVisit)).lower()
        self.assertIn('distinct', rendered)

    def test_avg_expression(self):
        expression = aggregates.Avg('content_id').expression(PageVisit)

        self.assertIn('avg', str(expression).lower())

    def test_unknown_field_raises_field_error(self):
        with self.assertRaises(FieldError):
            aggregates.Avg('time_spent').expression(PageVisit)

    def test_extract_hour_expression(self):
        expression = aggregates.ExtractHour('timestamp').expression(PageVisit)

        self.assertIn('timestamp', str(expression).lower())


class ValuesQueryTests(unittest.TestCase):

    def setUp(self):
        self.user = test_user()
        visit(self.user, '/makale/deneme-1', 'mobile', '10.0.0.1', hour=9)
        visit(self.user, '/makale/deneme-1', 'mobile', '10.0.0.1', hour=9)
        visit(self.user, '/makale/deneme-2', 'desktop', '10.0.0.2', hour=13)

    def queryset(self):
        return aggregates.queryset(PageVisit.query, PageVisit)

    def test_count_matches_the_underlying_query(self):
        self.assertEqual(self.queryset().count(), 3)

    def test_values_annotate_groups_rows(self):
        rows = list(
            self.queryset()
            .values('device_type')
            .annotate(count=aggregates.Count('id'))
            .order_by('device_type')
        )

        self.assertEqual(rows, [
            {'device_type': 'desktop', 'count': 1},
            {'device_type': 'mobile', 'count': 2},
        ])

    def test_order_by_descending(self):
        rows = list(
            self.queryset()
            .values('path')
            .annotate(visit_count=aggregates.Count('id'))
            .order_by('-visit_count')
        )

        self.assertEqual(rows[0]['path'], '/makale/deneme-1')
        self.assertEqual(rows[0]['visit_count'], 2)

    def test_distinct_count(self):
        rows = list(
            self.queryset()
            .values('path')
            .annotate(unique=aggregates.Count('ip_address', distinct=True))
            .order_by('path')
        )

        self.assertEqual([row['unique'] for row in rows], [1, 1])

    def test_extract_hour_annotation(self):
        rows = list(
            self.queryset()
            .annotate(hour=aggregates.ExtractHour('timestamp'))
            .values('hour')
            .annotate(count=aggregates.Count('id'))
            .order_by('hour')
        )

        self.assertEqual(rows, [
            {'hour': 9, 'count': 2},
            {'hour': 13, 'count': 1},
        ])

    def test_slice_limits_rows(self):
        rows = list(
            self.queryset()
            .values('path')
            .annotate(visit_count=aggregates.Count('id'))
            .order_by('-visit_count')[:1]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['path'], '/makale/deneme-1')

    def test_slice_with_an_offset(self):
        rows = list(
            self.queryset()
            .values('path')
            .annotate(visit_count=aggregates.Count('id'))
            .order_by('path')[1:2]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['path'], '/makale/deneme-2')

    def test_open_ended_slice(self):
        rows = list(
            self.queryset()
            .values('path')
            .annotate(visit_count=aggregates.Count('id'))
            .order_by('path')[1:]
        )

        self.assertEqual(len(rows), 1)

    def test_index_returns_a_single_row(self):
        row = (
            self.queryset()
            .values('path')
            .annotate(visit_count=aggregates.Count('id'))
            .order_by('path')
        )[0]

        self.assertEqual(row['path'], '/makale/deneme-1')

    def test_values_without_aggregates(self):
        rows = list(self.queryset().values('device_type').order_by(
            'device_type'
        ))

        self.assertEqual(rows, [
            {'device_type': 'desktop'},
            {'device_type': 'mobile'},
        ])

    def test_annotate_without_values_spans_every_row(self):
        rows = list(self.queryset().annotate(total=aggregates.Count('id')))

        self.assertEqual(rows, [{'total': 3}])

    def test_chained_values_accumulate(self):
        rows = list(
            self.queryset()
            .values('device_type')
            .values('browser')
            .annotate(count=aggregates.Count('id'))
            .order_by('device_type')
        )

        self.assertEqual(rows, [
            {'device_type': 'desktop', 'browser': 'Chrome', 'count': 1},
            {'device_type': 'mobile', 'browser': 'Chrome', 'count': 2},
        ])
