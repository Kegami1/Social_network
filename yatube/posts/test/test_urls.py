from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post

User = get_user_model()


class PostURLTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_follower = User.objects.create_user(username='test-user')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое поле'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            group=cls.group,
            author=cls.user
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client_follower = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_follower.force_login(self.user_follower)

    def test_urls_posts(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.post.author}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html'
        }

        for url, address in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, address)

    def test_author_edit_post(self):
        response = self.authorized_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, 200)

    def test_url_redirects(self):
        """Тестирование редиректов"""
        templates_url_names = {
            f'/posts/{self.post.id}/comment/': reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}),
            f'/profile/{self.user.username}/follow/': reverse(
                'posts:profile', kwargs={'username': self.user.username}),
            f'/profile/{self.user.username}/unfollow/': reverse(
                'posts:profile', kwargs={'username': self.user.username})
        }

        for url, address, in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client_follower.get(url)
                self.assertRedirects(response, address)

    def test_404_page(self):
        """Страница 404"""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, 404)
