from django import forms
from .models import Notification


class NotificationFilterForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Search...'}))
    type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + list(Notification.NotificationType.choices)
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status'), ('unread', 'Unread'), ('read', 'Read')]
    )
    priority = forms.ChoiceField(
        required=False,
        choices=[('', 'All Priorities')] + list(Notification.Priority.choices)
    )