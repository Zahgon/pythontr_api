from app.api.test import TestCase, Client
from core.models import get_user_model
from core.urls import reverse


class AdminSiteTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            email='pythontr@hotmail.com',
            password='123qwe'
        )

        self.client.force_login(self.admin_user)
        self.user = get_user_model().objects.create_user(
            email='test@hotmail.com',
            password='qwe321',
            name='pythontr'
        )

    def test_users_listed(self):
        url = reverse('core_user.index_view')
        res = self.client.get(url)

        self.assertContains(res, self.user.name)
        self.assertContains(res, self.user.email)

    def test_user_change_page(self):
        url = reverse('core_user.edit_view', kwargs={'id': self.user.id})
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_user_create(self):
        url = reverse('core_user.create_view')
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
