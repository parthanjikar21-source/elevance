from django import forms
from .models import Review, ReviewReport


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'title', 'content')
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select', 'id': 'rating-select'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Headline or summary of your review', 'id': 'review-title-input'}),
            'content': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Share your detailed thoughts, favorite moments, and cinematography impressions...', 'id': 'review-content-input'}),
        }


class ReviewReportForm(forms.ModelForm):
    class Meta:
        model = ReviewReport
        fields = ('reason', 'details')
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'details': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Provide details on why this review violates community standards...'}),
        }
