from django.contrib import admin
from .models import Genre, Language, CastMember, Movie, MovieCast, MoviePoster, Review, ReviewReport, UserRecentlyViewed


class MovieCastInline(admin.TabularInline):
    model = MovieCast
    extra = 2
    autocomplete_fields = ['cast_member']


class MoviePosterInline(admin.TabularInline):
    model = MoviePoster
    extra = 1


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(CastMember)
class CastMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'role')
    list_filter = ('role',)
    search_fields = ('name',)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'release_date', 'status', 'average_rating', 'total_reviews', 'is_trending')
    list_filter = ('status', 'is_trending', 'age_certification', 'genres', 'languages')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [MovieCastInline, MoviePosterInline]
    readonly_fields = ('average_rating', 'total_reviews')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('movie', 'user', 'rating', 'is_verified_viewer', 'is_flagged', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_verified_viewer', 'is_flagged', 'is_approved', 'created_at')
    search_fields = ('movie__title', 'user__username', 'title', 'content')
    actions = ['approve_reviews', 'flag_reviews']

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True, is_flagged=False)

    @admin.action(description="Flag selected reviews")
    def flag_reviews(self, request, queryset):
        queryset.update(is_flagged=True)


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ('review', 'reporter', 'reason', 'status', 'created_at')
    list_filter = ('reason', 'status', 'created_at')
    search_fields = ('review__movie__title', 'reporter__username', 'details')


@admin.register(UserRecentlyViewed)
class UserRecentlyViewedAdmin(admin.ModelAdmin):
    list_display = ('movie', 'user', 'session_key', 'viewed_at')
    list_filter = ('viewed_at',)
