from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username="author")
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)
        cls.group = Group.objects.create(
            title="Тестовый заголовок группы",
            slug="test-slug",
            description="test",
        )
        cls.post = Post.objects.create(
            text="Тестовая запись для создания нового поста",
            author=cls.author,
        )

    def test_pages_available_to_everyone(self):
        """Общедоступные страницы"""
        available_pages = [
            "/",
            f"/group/{self.group.slug}/",
            f"/profile/{self.author}/",
            f"/posts/{self.post.pk}/",
        ]

        for url in available_pages:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_author_post_url(self):
        """Страница доступна авторизованному автору поста."""
        response = self.authorized_client.get(f"/posts/{self.post.pk}/edit/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_post_url(self):
        """Страница доступна авторизованному пользователю."""
        response = self.authorized_client.get("/create/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_not_found_url(self):
        """404 страница"""
        response = self.authorized_client.get("/unexisting_page/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            "/": "posts/index.html",
            f"/group/{self.group.slug}/": "posts/group_list.html",
            f"/profile/{self.author}/": "posts/profile.html",
            f"/posts/{self.post.pk}/": "posts/post_detail.html",
            "/create/": "posts/create_post.html",
            f"/posts/{self.post.pk}/edit/": "posts/create_post.html",
        }

        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
