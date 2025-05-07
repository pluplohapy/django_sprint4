from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from .models import Post, Category


def get_published_posts():
    return Post.objects.select_related(
        'category', 'author', 'location'
    ).filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True,
    )


def index(request):
    template = 'blog/index.html'

    posts = get_published_posts()[:5]

    context = {'post_list': posts}
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'blog/detail.html'

    post = get_object_or_404(get_published_posts(), pk=post_id)

    context = {'post': post}
    return render(request, template, context)


def category_posts(request, category_slug):
    template = 'blog/category.html'

    category = get_object_or_404(
        Category.objects.filter(is_published=True),
        slug=category_slug,
    )

    posts = (
        get_published_posts()
        .filter(category=category)
    )

    context = {
        'post_list': posts,
        'category': category,
    }
    return render(request, template, context)
