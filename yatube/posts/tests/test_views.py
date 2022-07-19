import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from yatube.settings import PAGE_SIZE
from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.follower = User.objects.create_user(username="follower")
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.follower)

        cls.author = User.objects.create_user(username="author")
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)
        cls.group = Group.objects.create(
            title="Тестовый заголовок группы",
            slug="test-slug",
            description="test",
        )
        cls.another_group = Group.objects.create(
            title="Тестовый заголовок группы 2",
            slug="test-slug-2",
            description="test-2",
        )
        cls.post = Post.objects.create(
            text="Тестовая запись для создания нового поста",
            author=cls.author,
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse("posts:index"): "posts/index.html",
            reverse("posts:group_list",
                    kwargs={"slug": self.group.slug}):
            "posts/group_list.html",
            reverse("posts:profile",
                    kwargs={"username": self.author}):
            "posts/profile.html",
            reverse("posts:post_detail",
                    kwargs={"post_id": self.post.pk}):
            "posts/post_detail.html",
            reverse("posts:post_create"):
            'posts/create_post.html',
            reverse("posts:post_edit",
                    kwargs={"post_id": self.post.pk}):
            "posts/create_post.html",
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_context_for_index_group_profile(self):
        """Шаблоны index, group, profile
        сформированы с правильным контекстом"""
        template_pages = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.author}),
        )
        for template in template_pages:
            with self.subTest(template=template):
                response = self.authorized_client.get(template)
                first_post = response.context['page_obj'][0]
                post_author_0 = first_post.author
                post_text_0 = first_post.text
                post_group_0 = first_post.group.id
                post_image_0 = first_post.image
                self.assertEqual(post_author_0, self.post.author)
                self.assertEqual(post_text_0, self.post.text)
                self.assertEqual(post_group_0, self.post.group.id)
                self.assertEqual(post_image_0, self.post.image)

    def test_group_list_shows_correct_context(self):
        """Шаблон страницы группы сформирован
        с правильным контекстом."""
        response = self.authorized_client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
        )
        group = response.context["group"]
        self.assertEqual(group.title, self.group.title)
        self.assertEqual(group.slug, self.group.slug)
        self.assertEqual(group.description, self.group.description)

    def test_profile_shows_correct_context(self):
        """Шаблон страницы профиля сформирован
        с правильным контекстом."""
        response = self.authorized_client.get(
            reverse("posts:profile", kwargs={"username": self.author})
        )
        profile_user = response.context["author"]
        self.assertEqual(profile_user, self.author)

    def test_post_detail_shows_correct_context(self):
        """Шаблон страницы записи сформирован
        с правильным контекстом."""
        response = self.authorized_client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.pk})
        )
        post = response.context["post"]
        self.assertEqual(post, self.post)
        self.assertEqual(post.image, self.post.image)

    def test_post_edit_page_shows_correct_context(self):
        """В форму передаются данные
        соответствующие записи."""
        response = self.authorized_client.get(
            reverse("posts:post_edit", kwargs={"post_id": self.post.pk})
        )
        form_text = response.context["form"].instance.text
        form_group = response.context["form"].instance.group
        self.assertEqual(
            form_text, self.post.text
        )
        self.assertEqual(form_group, self.group)

    def test_create_post_shows_correct_context(self):
        """Шаблон страницы создания нового поста
        сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse("posts:post_create"))
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.fields.ChoiceField,
        }
        for field, field_class in form_fields.items():
            with self.subTest():
                form_field = response.context["form"].fields[field]
                self.assertIsInstance(form_field, field_class)

    def test_post_appeared_index_group_profile(self):
        """Тестовый пост на главной странице,
        странице группы, в профаиле."""
        pages = [
            (reverse("posts:index")),
            reverse("posts:group_list", kwargs={"slug": self.group.slug}),
            reverse("posts:profile", kwargs={"username": self.author}),
        ]
        for url in pages:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                posts = response.context["page_obj"]
                self.assertIn(self.post, posts)

    def test_post_not_appeared_group(self):
        """Тестовый пост не появляется на странице
        чужой группы, в которую он не включён."""
        response = self.authorized_client.get(
            reverse(
                "posts:group_list", kwargs={"slug": self.another_group.slug}
            )
        )
        posts = response.context["page_obj"]
        self.assertNotIn(self.post, posts)

    def test_cache_index_page(self):
        """Кэш страницы index работает корректно"""
        response = self.authorized_client.get(reverse('posts:index'))
        context = response.content
        Post.objects.create(
            text=self.post.text,
            author=self.author,
            group=self.group,
        )
        response = self.authorized_client.get(reverse('posts:index'))
        context_add = response.content
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        context_clear = response.content
        self.assertEqual(context, context_add)
        self.assertNotEqual(context, context_clear)

    def test_follow_users(self):
        """Авторизованный пользователь может подписываться
        на других пользователей."""
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.follower}
            )
        )
        follower_add = Follow.objects.count()
        self.assertEqual(follower_add, follow_count + 1)

    def test_unfollow_users(self):
        """Авторизованный пользователь может отписаться от
        пользователей."""
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.follower}
            )
        )
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.follower}
            )
        )
        unfollow_count = Follow.objects.count()
        self.assertEqual(follow_count, unfollow_count)

    def test_follow_posts(self):
        """Посты отобразились у подписчика и наоборот, если не подписан."""
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.follower})
        )
        new_post = Post.objects.create(
            text=self.post.text,
            author=self.follower,
            group=self.group,
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        follow_post = response.context['page_obj'][0]
        self.assertEqual(follow_post, new_post)
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_i_not_can_subscribe_to_myself(self):
        """Не может подписаться на самого себя"""
        self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.author}))
        follow = Follow.objects.filter(user=self.author).count()
        self.assertEqual(follow, 0)


class PostPaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_client = Client()
        cls.author = User.objects.create_user(username="author")
        cls.authorized_client.force_login(cls.author)
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        Post.objects.bulk_create(
            [
                Post(
                    text=f"Тестовый пост {x}",
                    author=cls.author,
                    group=cls.group,
                )
                for x in range(13)
            ]
        )
        cls.page_names = {
            reverse("posts:index"),
            reverse("posts:group_list", kwargs={"slug": cls.group.slug}),
            reverse("posts:profile", kwargs={"username": cls.author}),
        }

    def test_first_page(self):
        """Проверка: количество постов на первой странице равно 10."""
        for reverse_name in self.page_names:
            response = self.authorized_client.get(reverse_name)
        self.assertEqual(len(response.context["page_obj"]), PAGE_SIZE)

    def test_second_page(self):
        """Проверка: количество постов на второй странице равно 3."""
        post_count = Post.objects.count()
        for reverse_name in self.page_names:
            response = self.authorized_client.get(reverse_name + "?page=2")
            self.assertEqual(
                len(response.context["page_obj"]), post_count - PAGE_SIZE)
