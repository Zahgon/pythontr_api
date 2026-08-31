import os
import unittest

from flask import current_app

from core import storage
from core.models import Article, Category, get_user_model


def test_user(email='storage@hotmail.com', password='123qwe'):
    return get_user_model().objects.create_user(email, password)


class StorageTests(unittest.TestCase):

    def setUp(self):
        self.root = storage.media_root()
        self.written = []

    def tearDown(self):
        for name in self.written:
            storage.delete(name)

    def record(self, name):
        self.written.append(name)
        return name

    def test_media_root_is_the_project_directory(self):
        self.assertEqual(
            str(self.root), current_app.config['BASE_DIR']
        )

    def test_save_writes_the_file_and_returns_the_name(self):
        name = self.record(storage.save('static/probe/one.txt', b'merhaba'))

        self.assertEqual(name, 'static/probe/one.txt')
        with open(self.root / name, 'rb') as handle:
            self.assertEqual(handle.read(), b'merhaba')

    def test_save_accepts_a_file_object(self):
        content = storage.ContentFile(b'icerik', name='two.txt')
        name = self.record(storage.save('static/probe/two.txt', content))

        with open(self.root / name, 'rb') as handle:
            self.assertEqual(handle.read(), b'icerik')

    def test_save_encodes_text_content(self):
        content = storage.ContentFile('gövde', name='three.txt')
        name = self.record(storage.save('static/probe/three.txt', content))

        with open(self.root / name, 'rb') as handle:
            self.assertEqual(handle.read().decode('utf-8'), 'gövde')

    def test_save_suffixes_a_taken_name(self):
        first = self.record(storage.save('static/probe/dup.txt', b'one'))
        second = self.record(storage.save('static/probe/dup.txt', b'two'))

        self.assertEqual(first, 'static/probe/dup.txt')
        self.assertNotEqual(second, first)
        self.assertTrue(second.startswith('static/probe/dup_'))
        self.assertTrue(second.endswith('.txt'))
        with open(self.root / second, 'rb') as handle:
            self.assertEqual(handle.read(), b'two')

    def test_get_available_name_leaves_a_free_name_alone(self):
        self.assertEqual(
            storage.get_available_name('static/probe/free.txt'),
            'static/probe/free.txt',
        )

    def test_move_relocates_the_file(self):
        old = storage.save('static/probe/temp/moved.txt', b'tasi')
        new = self.record(storage.move(old, 'static/probe/1/moved.txt'))

        self.assertEqual(new, 'static/probe/1/moved.txt')
        self.assertFalse((self.root / old).exists())
        with open(self.root / new, 'rb') as handle:
            self.assertEqual(handle.read(), b'tasi')

    def test_move_returns_the_old_name_when_there_is_nothing_to_move(self):
        self.assertEqual(
            storage.move('static/probe/missing.txt', 'static/probe/x.txt'),
            'static/probe/missing.txt',
        )

    def test_move_suffixes_a_taken_destination(self):
        taken = self.record(storage.save('static/probe/1/busy.txt', b'ilk'))
        old = storage.save('static/probe/temp/busy.txt', b'ikinci')
        new = self.record(storage.move(old, 'static/probe/1/busy.txt'))

        self.assertNotEqual(new, taken)
        with open(self.root / taken, 'rb') as handle:
            self.assertEqual(handle.read(), b'ilk')
        with open(self.root / new, 'rb') as handle:
            self.assertEqual(handle.read(), b'ikinci')

    def test_delete_removes_the_file(self):
        name = storage.save('static/probe/gone.txt', b'sil')
        storage.delete(name)

        self.assertFalse((self.root / name).exists())

    def test_delete_ignores_an_empty_name(self):
        self.assertIsNone(storage.delete(''))

    def test_delete_ignores_a_missing_file(self):
        self.assertIsNone(storage.delete('static/probe/never.txt'))

    def test_content_file_reads_back_its_content(self):
        content = storage.ContentFile(b'veri', name='four.txt')

        self.assertEqual(content.read(), b'veri')
        self.assertEqual(content.name, 'four.txt')

    def test_persist_passes_none_through(self):
        self.assertIsNone(storage.persist(None, None, None))

    def test_persist_passes_an_existing_name_through(self):
        self.assertEqual(
            storage.persist(None, 'static/img/kept.webp', None),
            'static/img/kept.webp',
        )

    def test_persist_stores_an_upload(self):
        user = test_user()
        category = Category.objects.create(
            user=user, name='Depolama', short_name='depolama'
        )
        article = Article(
            title='Depolama Makalesi',
            title_h1='Depolama Makalesi',
            user=user,
        )
        article.categories.append(category)
        article.save()

        from core.models.model_article import article_image_file_path

        content = storage.ContentFile(b'resim', name='kapak.png')
        name = self.record(
            storage.persist(article, content, article_image_file_path)
        )

        self.assertEqual(
            name, 'static/article/{}/kapak.png'.format(article.pk)
        )
        with open(self.root / name, 'rb') as handle:
            self.assertEqual(handle.read(), b'resim')

    def test_persist_reads_a_werkzeug_filename(self):
        class Upload:
            filename = 'avatar.png'

            def read(self):
                return b'avatar'

        user = test_user(email='avatar@hotmail.com')
        from core.models.model_user import avatar_image_file_path

        name = self.record(
            storage.persist(user, Upload(), avatar_image_file_path)
        )

        self.assertEqual(
            name, 'static/avatar/{}/avatar.png'.format(user.pk)
        )

    def test_saved_directories_are_created(self):
        name = self.record(
            storage.save('static/probe/deep/nested/leaf.txt', b'derin')
        )

        self.assertTrue(os.path.isdir(os.path.dirname(self.root / name)))
