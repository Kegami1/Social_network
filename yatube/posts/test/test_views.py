from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache

from yatube.settings import POSTS_ON_PAGE
from posts.models import Group, Post, Follow

User = get_user_model()


class PostViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое поле'
        )
        cls.group2 = Group.objects.create(
            title='Тестовый заголовок2',
            slug='test-slug2',
            description='Тестовое поле2'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            group=cls.group,
            author=cls.user
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs=(
                {'username': self.user.username})):
                    'posts/profile.html',
            reverse('posts:post_detail', kwargs=(
                {'post_id': self.post.id})):
                    'posts/post_detail.html',
            reverse('posts:post_edit', kwargs=(
                {'post_id': self.post.id})):
                    'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html'
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_context_index(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        test_post = response.context.get('page_obj')[0]
        self.assertEqual(test_post.text, self.post.text)
        self.assertEqual(test_post.group, self.post.group)
        self.assertEqual(test_post.author, self.post.author)

    def test_context_group_list(self):
        """Шаблон group_list правильно сформирован с фильтром по группам"""
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs=(
                {'slug': self.group.slug}
            )))
        test_post = response.context.get('page_obj')[0]
        self.assertEqual(test_post.group.slug, self.group.slug)

    def test_context_profile(self):
        """Шаблон profile правильно сформирован с фильтром по пользователю"""
        response = self.authorized_client.get(reverse('posts:profile', kwargs=(
            {'username': self.post.author}
        )))
        test_post = response.context.get('page_obj')[0]
        self.assertEqual(test_post.author, self.post.author)

    def test_context_post_detail(self):
        """Шаблон post_detail правильно сформирован с информацией по посту"""
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs=(
                {'post_id': self.post.id}
            )))
        test_post = response.context.get('post')
        self.assertEqual(test_post.id, self.post.id)

    def test_context_post_create(self):
        """Шаблон post_create создан верно"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_context_post_edit(self):
        """Шаблон post_edit с фильтром по id создан верно"""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs=(
                {'post_id': self.post.id}
            )))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_in_group(self):
        """После создания пост корректно появляется на главной странице,
        в группе и в профиле автора"""
        response = self.authorized_client.get(reverse('posts:index'))
        index_post = response.context['page_obj'][0]
        self.assertEqual(index_post, self.post)
        reseponse = self.authorized_client.get(reverse(
            'posts:group_list', kwargs=(
                {'slug': self.group.slug}
            )))
        group_list_post = reseponse.context['page_obj'][0]
        self.assertEqual(group_list_post, self.post)
        reseponse = self.authorized_client.get(reverse(
            'posts:profile', kwargs=(
                {'username': self.post.author}
            )))
        profile_post = response.context['page_obj'][0]
        self.assertEqual(profile_post, self.post)

    def test_post_only_in_chosen_group(self):
        """Пост попадает только в ту группу в которой был создан"""
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs=(
                {'slug': self.group2.slug}
            )))
        page_object = response.context.get('page_obj').object_list
        self.assertNotIn(self.post, page_object)

    def test_cache_index(self):
        """Контент на странице корректно кэшируется"""
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        posts_cache = response.content
        post = Post.objects.first()
        post.delete()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, posts_cache)
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, posts_cache)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое поле'
        )
        posts_list = [
            Post(
                text=f'Тестовый текст {i}',
                author=cls.user,
                group=cls.group
            ) for i in range(25)
        ]
        Post.objects.bulk_create(posts_list)
        cls.posts = Post.objects.all()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_paginator(self):
        """Паджинатор правильно выводит кол-во постов"""
        test_dict = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs=({'slug': self.group.slug})),
            reverse('posts:profile', kwargs=(
                {'username': self.posts[0].author})),
        }

        for test in test_dict:
            response = self.authorized_client.get(test)
            self.assertEqual(len(response.context['page_obj']), POSTS_ON_PAGE)
            posts_count = Post.objects.count()
            i = 2
            while posts_count > POSTS_ON_PAGE:
                response = self.authorized_client.get((test + f'?page={i}'))
                i += 1
                posts_count -= POSTS_ON_PAGE
            self.assertEqual(len(response.context['page_obj']), posts_count)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_follower = User.objects.create_user(username='test_user')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client_follower = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_follower.force_login(self.user_follower)

    def test_auth_user_can_follow(self):
        """Авторизированный пользователь может подписываться
        на пользователей"""
        self.authorized_client_follower.get(reverse(
            'posts:profile_follow', kwargs={'username': self.user}))
        self.assertEqual(Follow.objects.count(), 1)

    def test_auth_user_can_unfollow(self):
        """Авторизированный пользователь может отписываться
        от пользователей"""
        Follow.objects.create(
            user=self.user_follower,
            author=self.user
        )
        self.authorized_client_follower.get(reverse(
            'posts:profile_unfollow', kwargs={'username': self.user}
        ))
        self.assertEqual(Follow.objects.count(), 0)

    def test_new_post_for_follower(self):
        """Новый пост корректно отображается в ленте
        у пользователей подписавшихся на автора"""
        Follow.objects.create(
            user=self.user_follower,
            author=self.user
        )
        new_post = Post.objects.create(
            text='Новый пост для фоловеров',
            author=self.user
        )
        response = self.authorized_client_follower.get(reverse(
            'posts:follow_index'))
        follow_post = response.context['page_obj'][0]
        self.assertEqual(follow_post.text, new_post.text)

    def test_new_post_for_other_users(self):
        """Новый пост не появляется в ленте у пользвателей
        которые не подписаны на автора"""
        new_post = Post.objects.create(
            text='Новый пост для фоловеров',
            author=self.user
        )
        response_author = self.authorized_client.get(reverse(
            'posts:follow_index'))
        self.assertNotIn(new_post, response_author.context['page_obj'])
