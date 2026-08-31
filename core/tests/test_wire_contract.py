"""The parts of the wire contract that carried no test.

`app/api/messages.py` states that the Turkish error strings are part of the
public contract of this service and that clients match on them, and the
migration's whole delta-lever is that the shapes DRF produced had to survive
the dependency being removed. A mutation run showed that none of it was
asserted anywhere: re-translating the strings, changing the token keyword, or
downgrading a 415 to a 400 left all 205 tests passing.

The strings below are written out literally rather than imported from
`app.api.messages`. Importing the constant would move the test and the code
together, so a re-translation would still pass -- which is exactly how this
surface came to be unguarded.
"""
from core.models import get_user_model
from core.urls import reverse

from app.api import status
from app.api.test import APIClient, TestCase


MESSAGES_URL = reverse('recipe:message-list')


def detail_url(id=1):
    return reverse('recipe:message-detail', args=[id])


class ErrorContractTests(TestCase):
    """The error bodies clients match on, asserted verbatim."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'contract@hotmail.com',
            '123qwe',
        )

    def test_anonymous_request_returns_turkish_not_authenticated(self):
        res = self.client.get(MESSAGES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            res.data['detail'], 'Giriş bilgileri verilmedi.')

    def test_unsupported_method_returns_turkish_detail_with_verb(self):
        self.client.force_authenticate(self.user)
        res = self.client.delete(detail_url(1))

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(
            res.data['detail'],
            '"DELETE" metoduna izin verilmiyor.',
        )

    def test_unauthorised_returns_turkish_permission_detail(self):
        self.client.force_authenticate(self.user)
        res = self.client.post(
            reverse('recipe:category-list'),
            {'name': 'contract', 'short_name': 'ct'},
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            res.data['detail'], 'Bu işlemi yapmak için izniniz bulunmuyor.')

    def test_unsupported_media_type_is_415_not_400(self):
        self.client.force_authenticate(self.user)
        res = self.client.post(
            MESSAGES_URL,
            data='<xml/>',
            content_type='application/xml',
        )

        self.assertEqual(
            res.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)


class TokenHeaderTests(TestCase):
    """The `Authorization: Token <key>` grammar.

    Every other test signs in with `force_authenticate`, which installs
    the user directly and never exercises the header. Changing the keyword
    to `Bearer` broke no test at all while breaking every real client.

    The header is passed straight to the request rather than through
    `APIClient.credentials()`: that method stores its keyword arguments in
    `self._headers` and `_request` never reads them, so it is a silent no-op.
    No shipped test calls it, which is why the gap survived. It is
    reported separately; these tests do not depend on it.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'token@hotmail.com',
            '123qwe',
        )
        # A user is created inactive; authentication rejects an inactive user
        # before it ever looks at the keyword, so the positive case needs one
        # that is active.
        self.user.is_active = True
        self.user.save()
        self.inactive = get_user_model().objects.create_user(
            'inactive-token@hotmail.com',
            '123qwe',
        )

    def test_token_keyword_authenticates(self):
        from core.models import Token

        token, _ = Token.get_or_create(user=self.user)
        res = self.client.get(
            MESSAGES_URL,
            headers={'Authorization': 'Token {}'.format(token.key)},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_inactive_user_returns_turkish_inactive_detail(self):
        from core.models import Token

        token, _ = Token.get_or_create(user=self.inactive)
        res = self.client.get(
            MESSAGES_URL,
            headers={'Authorization': 'Token {}'.format(token.key)},
        )

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            res.data['detail'], 'Kullanıcı aktif değil ya da silinmiş')

    def test_credentials_sets_the_header_for_later_requests(self):
        """``credentials()`` used to store its arguments and drop them.

        ``_request`` read only the headers passed to the call itself, so a
        test signing in this way authenticated as anonymous. No shipped test
        called it, so nothing failed.
        """
        from core.models import Token

        token, _ = Token.get_or_create(user=self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION='Token {}'.format(token.key))
        res = self.client.get(MESSAGES_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_credentials_accepts_a_plain_header_name(self):
        from core.models import Token

        token, _ = Token.get_or_create(user=self.user)
        self.client.credentials(
            Authorization='Token {}'.format(token.key))
        res = self.client.get(MESSAGES_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_another_keyword_is_not_accepted(self):
        from core.models import Token

        token, _ = Token.get_or_create(user=self.user)
        res = self.client.get(
            MESSAGES_URL,
            headers={'Authorization': 'Bearer {}'.format(token.key)},
        )

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
