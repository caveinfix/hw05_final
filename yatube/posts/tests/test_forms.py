import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import CommentForm, PostForm
from ..models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username="author")
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title="Тестовый заголовок группы",
            slug="test-slug",
            description="test",
        )
        cls.post = Post.objects.create(
            text="Тестовая запись для создания нового поста",
            author=cls.author,
            group=cls.group,
            image=cls.uploaded,
        )
        cls.group = Group.objects.create(
            title="Тестовый заголовок группы 2",
            slug="test-slug-2",
            description="test-2",
        )
        cls.form = PostForm()
        cls.form = CommentForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_count_post_form(self):
        """При отправке валидной формы создается запись в БД."""
        count_post = Post.objects.count()
        form_data = {
            "text": self.post.text,
            'image': self.post.image,
        }
        response = self.authorized_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response,
            reverse("posts:profile", kwargs={"username": self.author}),
        )
        last_post = Post.objects.latest('pk')
        self.assertEqual(Post.objects.count(), count_post + 1)
        self.assertTrue(last_post.text, self.post.text)
        self.assertTrue(last_post.image, self.uploaded)

    def test_edit_post_form(self):
        """При редактировании поста, происходит изменение в БД."""
        form_data = {
            "text": self.post.text,
            'group': self.group.pk,
        }
        response = self.authorized_client.post(
            reverse("posts:post_edit", kwargs={"post_id": self.post.pk}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse("posts:post_detail", kwargs={"post_id": self.post.pk}),
        )
        select_post = Post.objects.get(pk=self.post.pk)
        self.assertTrue(
            select_post.text == form_data['text']
        )
        self.assertTrue(
            select_post.group.pk == form_data['group']
        )

    def test_add_comment(self):
        """Комментарий создан авторизованным пользователям
        и появился на странице поста"""
        comments_count = Comment.objects.count()
        form_data = {
            'text': self.post.text,
            'post': self.post.id
        }
        response = self.authorized_client.post(
            reverse("posts:add_comment", kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )

        last_comment = Comment.objects.latest('pk')
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            last_comment.text == form_data['text']
        )
        self.assertTrue(
            last_comment.post == self.post
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.pk}))
