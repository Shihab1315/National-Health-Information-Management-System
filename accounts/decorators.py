from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(allowed_roles, redirect_url='/', login_url='accounts:login'):
    """
    Decorator to restrict access to views based on user role.
    """

    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            # User logged in কিনা
            if not request.user.is_authenticated:
                print("❌ User not authenticated")
                return redirect(login_url)

            # ===== DEBUG =====
            print("\n========== RBAC DEBUG ==========")
            print("Username :", request.user.username)
            print("Role     :", request.user.role)
            print("Allowed  :", allowed_roles)
            print("Has Role :", request.user.has_role(allowed_roles))
            print("===============================\n")

            # Permission check
            if not request.user.has_role(allowed_roles):
                messages.error(
                    request,
                    "You do not have permission to access this page."
                )
                print("❌ Permission Denied")
                return redirect(redirect_url)

            print("✅ Permission Granted")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


# -------------------------------
# Shortcut decorators
# -------------------------------

def super_admin_required(view_func):
    return role_required('super_admin')(view_func)


def hospital_admin_required(view_func):
    return role_required(['super_admin', 'hospital_admin'])(view_func)


def staff_required(view_func):
    return role_required([
        'super_admin',
        'hospital_admin',
        'doctor',
        'receptionist',
        'lab_technician',
        'pharmacist'
    ])(view_func)


def doctor_or_admin_required(view_func):
    return role_required([
        'super_admin',
        'hospital_admin',
        'doctor'
    ])(view_func)