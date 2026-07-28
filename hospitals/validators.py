from django.core.exceptions import ValidationError
import re

def validate_phone(value):
    pattern = r'^\+?[0-9]{10,15}$'
    if not re.match(pattern, value):
        raise ValidationError('Enter a valid phone number (10-15 digits, optionally starting with +).')

def validate_email(value):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValidationError('Enter a valid email address.')

def validate_website(value):
    pattern = r'^(https?://)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    if not re.match(pattern, value):
        raise ValidationError('Enter a valid URL (e.g., https://example.com).')

def validate_latitude(value):
    if value and not (-90 <= value <= 90):
        raise ValidationError('Latitude must be between -90 and 90.')

def validate_longitude(value):
    if value and not (-180 <= value <= 180):
        raise ValidationError('Longitude must be between -180 and 180.')