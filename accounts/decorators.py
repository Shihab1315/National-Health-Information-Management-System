from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(allowed_roles, redirect_url=None, login_url='accounts:login'):
    """
    Decorator to restrict access to views based on user role.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect(login_url)

            # Permission check
            if not request.user.has_role(allowed_roles):
                messages.error(
                    request,
                    "You do not have permission to access this page."
                )
                
                # ✅ Dynamic redirect based on user role
                if redirect_url:
                    return redirect(redirect_url)
                else:
                    # Default redirect based on role
                    if request.user.role == 'doctor':
                        return redirect('dashboard:doctor_dashboard')
                    elif request.user.role == 'patient':
                        return redirect('dashboard:patient_dashboard')
                    elif request.user.role == 'super_admin':
                        return redirect('superadmin:dashboard')
                    elif request.user.role == 'hospital_admin':
                        return redirect('hospital_admin:dashboard')
                    else:
                        return redirect('dashboard:homepage')

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator