from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.db.models import Count
from django.utils import timezone
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic import DeleteView

from .forms import UserEditForm, CommentForm, PostForm
from .models import Post, Category, Comment


def published_posts(base_qs):
    return (
        base_qs.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
            location__is_published=True)
        .select_related('author', 'category', 'location')
        .annotate(comment_count=Count('comments'))
        .order_by('-pub_date')
    )


def paginate(request, queryset, per_page):
    paginator = Paginator(queryset, per_page)
    page = request.GET.get('page')
    return paginator.get_page(page)


def index(request):
    template = 'blog/index.html'
    qs = published_posts(Post.objects.all())
    page_obj = paginate(request, qs, per_page=10)
    return render(request, template, {'page_obj': page_obj})


def category_posts(request, category_slug):
    template = 'blog/category.html'
    category = get_object_or_404(
        Category.objects.filter(is_published=True),
        slug=category_slug
    )
    qs = published_posts(Post.objects.filter(category=category))
    page_obj = paginate(request, qs, per_page=10)

    return render(request, template, {
        'page_obj': page_obj,
        'category': category
    })


def profile(request, username):
    template = 'blog/profile.html'

    user = get_object_or_404(User, username=username)
    posts = (Post.objects
             .filter(author=user)
             .annotate(comment_count=Count('comments'))
             .order_by('-pub_date'))
    if not request.user.is_authenticated or request.user != user:
        posts = posts.filter(is_published=True, pub_date__lte=timezone.now())

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, template, {'profile': user, 'page_obj': page_obj})


@login_required
def edit_profile(request):
    template_name = 'blog/user.html'
    form = UserEditForm(request.POST or None, instance=request.user)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user)

    return render(request, template_name, {'form': form})


def post_detail(request, post_id):
    template_name = 'blog/detail.html'
    post = get_object_or_404(Post, pk=post_id)

    user = request.user
    is_author = user.is_authenticated and user == post.author
    is_future_post = post.pub_date > timezone.now()

    if is_future_post and not is_author:
        raise Http404("Пост еще не опубликован.")

    is_visible = (
        post.is_published
        and post.category.is_published
        and post.location.is_published
    )

    if not is_visible and not is_author:
        raise Http404("Пост недоступен.")

    comments = Comment.objects.filter(
        is_published=True,
        post=post
    ).select_related('author')
    form = CommentForm()

    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }

    return render(request, template_name, context)


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:index')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        user = request.user

        if (not user.is_authenticated
                or (user != self.object.author and not user.is_staff)):
            return redirect('blog:post_detail', post_id=self.object.pk)
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author


class PostEditView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        if (not request.user.is_authenticated
                or request.user != self.object.author):
            return redirect('blog:post_detail', post_id=self.object.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.pk}
        )


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()

    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    template_name = 'blog/comment.html'
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post_id=post_id,
        author=request.user
    )
    form = CommentForm(request.POST or None, instance=comment)

    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)

    return render(request, template_name, {'form': form, 'comment': comment})


@login_required
def delete_comment(request, post_id, comment_id):
    template_name = 'blog/comment.html'
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post_id=post_id,
        author=request.user
    )

    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)

    return render(request, template_name, {'comment': comment})
