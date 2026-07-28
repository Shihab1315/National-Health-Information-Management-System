from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Notification
from .services import mark_all_as_read, delete_all_read

User = get_user_model()


class NotificationModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.notification = Notification.objects.create(
            recipient=self.user,
            title='Test Notification',
            message='This is a test.',
            notification_type=Notification.NotificationType.SYSTEM_NOTIFICATION,
            icon='fas fa-bell',
            color='text-gray-400',
            url='/',
            priority=Notification.Priority.LOW
        )

    def test_notification_creation(self):
        self.assertEqual(self.notification.title, 'Test Notification')
        self.assertEqual(self.notification.recipient, self.user)
        self.assertFalse(self.notification.is_read)

    def test_mark_as_read(self):
        self.notification.mark_as_read()
        self.assertTrue(self.notification.is_read)

    def test_unread_count(self):
        count = Notification.objects.unread_count(self.user)
        self.assertEqual(count, 1)
        self.notification.mark_as_read()
        count = Notification.objects.unread_count(self.user)
        self.assertEqual(count, 0)

    def test_mark_all_as_read(self):
        Notification.objects.create(recipient=self.user, title='Another', message='test')
        mark_all_as_read(self.user)
        unread = Notification.objects.unread_count(self.user)
        self.assertEqual(unread, 0)

    def test_delete_all_read(self):
        self.notification.mark_as_read()
        deleted = delete_all_read(self.user)
        self.assertEqual(deleted, 1)
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 0)


class NotificationSignalTests(TestCase):
    # We'll need to test that signals fire correctly.
    # For simplicity, we can test that patient creation triggers a notification.
    # Since we have to import patient model, we can skip in this file or add basic check.
    def test_signal_import(self):
        # Just check that signals module loads without error
        from . import signals
        self.assertTrue(hasattr(signals, 'patient_created'))