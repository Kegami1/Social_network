import shutil
import tempfile


from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from posts.models import Group, Post
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from django.urls import reverse

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CoreViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое поле'
        )
        cls.image1 = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploader = SimpleUploadedFile(
            name='Test_image.gif',
            content=cls.image1,
            content_type='image'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            group=cls.group,
            author=cls.user,
            image=cls.uploader
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_views(self):
        test_list = {
            reverse('posts:index'): 'page_obj',
            reverse('posts:profile', kwargs={
                'username': self.post.author}): 'page_obj',
            reverse('posts:group_list', kwargs={
                'slug': self.group.slug}): 'page_obj',

        }

        for address, context in test_list.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                test_page = response.context.get(context)[0].image
                self.assertEqual(test_page, self.post.image)

    def test_views_image_post_detail(self):
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        test_page = response.context.get('post')
        self.assertEqual(test_page.image, self.post.image)

    def test_create_post_with_image(self):
        post_count = Post.objects.count()
        uploader = SimpleUploadedFile(
            name='Test_image.gif',
            content=self.image1,
            content_type='image'
        )
        data_image = {
            'text': 'Пост с картинкой',
            'group': self.group.id,
            'author': self.post.author,
            'image': uploader
        }
        response = self.authorized_client.post(reverse(
            'posts:post_create'), data_image, Follow=True)
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertRedirects(response, reverse('posts:profile', kwargs={
            'username': self.post.author}))
