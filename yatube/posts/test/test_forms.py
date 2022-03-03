import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TestPostForm(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            group=cls.group
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.guest_client = Client()

    def test_create_post(self):
        """Пост был успешно создан и добавлен в базу"""
        post_count = Post.objects.count()
        form_data = {
            'author': self.user,
            'text': 'Тестовая пост',
            'group': self.group.id
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        test_post = Post.objects.get(id=self.post.pk)
        self.assertEqual(test_post.text, self.post.text)
        self.assertEqual(test_post.author, self.post.author)
        self.assertEqual(test_post.group.id, self.post.group.id)
        self.assertRedirects(response, reverse('posts:profile', kwargs=(
            {'username': self.post.author}
        )))
        self.assertEqual(Post.objects.count(), post_count + 1)

    def test_edit_post(self):
        """Пост корректно сохраняется после его редактирования"""
        text = self.post.text
        form_data = {
            'text': 'Измененный текст'
        }
        response = self.authorized_client.post(reverse(
            'posts:post_edit', kwargs=(
                {'post_id': self.post.id})),
            data=form_data,
            follow=True)
        edited_post = Post.objects.get(id=self.post.pk)
        self.assertNotEqual(edited_post, text)
        self.assertRedirects(response, reverse('posts:post_detail', kwargs=(
            {'post_id': self.post.id}
        )))

    def test_post_creation_auth(self):
        """Посты могут создавать только авторизированные пользователи"""
        posts_count = Post.objects.count()
        response = self.guest_client.post(reverse('posts:post_create'))
        self.assertEqual(Post.objects.count(), posts_count)
        url_login = reverse('users:login')
        url_create = reverse('posts:post_create')
        self.assertRedirects(response, f'{url_login}?next={url_create}')


class CommentViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
        )
        cls.comment = Comment.objects.create(
            text='Тестовый коммент',
            post=cls.post,
            author=cls.user
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_comments(self):
        """Комментарий корректно появляется на странице поста"""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Новый комментарий',
        }

        response = self.authorized_client.post(reverse(
            'posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        test_comment = Comment.objects.order_by('-id')[0]
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={
            'post_id': self.post.pk}))
        self.assertEqual(test_comment.text, form_data.get('text'))
        self.assertEqual(test_comment.author, self.user)

    def test_comments_only_for_auth_users(self):
        """Комментарии не могут оставлять юзеры-гости"""
        response = self.guest_client.get(reverse(
            'posts:add_comment', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.status_code, 302)
        url_login = reverse('users:login')
        url_comment = reverse('posts:add_comment', kwargs={
            'post_id': self.post.id
        })
        self.assertRedirects(response, f'{url_login}?next={url_comment}')
