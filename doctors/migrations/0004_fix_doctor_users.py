# doctors/migrations/0004_fix_doctor_users.py
from django.db import migrations, transaction
from django.contrib.auth.models import User


def generate_unique_username(license_number, model):
    """Generate a unique username from license number."""
    base = f"dr_{license_number.lower().replace(' ', '_')}"
    # Remove special characters
    base = ''.join(c for c in base if c.isalnum() or c == '_')
    
    # Ensure uniqueness
    counter = 1
    username = base[:150]  # Max length for username
    while model.objects.filter(username=username).exists():
        username = f"{base[:140]}_{counter}"[:150]
        counter += 1
    
    return username


def fix_doctor_users(apps, schema_editor):
    """
    Link existing doctors without User accounts to new Users.
    This runs BEFORE the NOT NULL constraint is applied.
    """
    Doctor = apps.get_model('doctors', 'Doctor')
    User = apps.get_model('auth', 'User')
    
    doctors_fixed = 0
    doctors_failed = 0
    
    # Get all doctors without User accounts
    orphan_doctors = Doctor.objects.filter(user__isnull=True)
    
    print(f"\n🔍 Found {orphan_doctors.count()} doctors without User accounts")
    
    for doctor in orphan_doctors:
        try:
            with transaction.atomic():
                # Generate username from registration number
                username = generate_unique_username(
                    doctor.registration_number or f"doc_{doctor.id}", 
                    User
                )
                
                # Use email if available, otherwise generate
                email = doctor.email if doctor.email else f"{username}@nhims.local"
                
                # Generate a random password
                password = User.objects.make_random_password(length=12)
                
                # Create User
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                
                # Set first_name and last_name
                if doctor.full_name and doctor.full_name != 'Unknown':
                    name_parts = doctor.full_name.split(maxsplit=1)
                    user.first_name = name_parts[0] if name_parts else ''
                    user.last_name = name_parts[1] if len(name_parts) > 1 else ''
                else:
                    user.first_name = 'Doctor'
                    user.last_name = doctor.registration_number or ''
                
                user.save()
                
                # Link User to Doctor
                doctor.user = user
                doctor.save()
                
                doctors_fixed += 1
                print(f"✅ Fixed doctor: {doctor.full_name} -> {username}")
                
        except Exception as e:
            doctors_failed += 1
            print(f"❌ Failed to fix doctor {doctor.id} ({doctor.full_name}): {e}")
    
    print(f"\n📊 Summary:")
    print(f"   ✅ Fixed: {doctors_fixed} doctors")
    print(f"   ❌ Failed: {doctors_failed} doctors")


def reverse_fix(apps, schema_editor):
    """
    Reverse migration - warn about data loss.
    """
    print("\n⚠️  WARNING: Reverse migration will NOT remove User accounts.")
    print("   To rollback, you must manually handle User accounts.")
    print("   This migration is not reversible to avoid data loss.")


class Migration(migrations.Migration):
    dependencies = [
        ('doctors', '0003_doctoravailability_alter_doctor_is_active_and_more'),  # আপনার শেষ মাইগ্রেশন
    ]

    operations = [
        migrations.RunPython(fix_doctor_users, reverse_fix),
    ]