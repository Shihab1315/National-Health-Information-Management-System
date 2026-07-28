from django.apps import AppConfig

class MedicalRecordsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'medical_records'
    verbose_name = 'Medical Records'

    def ready(self):
        import medical_records.signals