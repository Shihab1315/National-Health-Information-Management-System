from django import template

register = template.Library()


@register.filter(name='has_role')
def has_role(user, role):
    """Check if user has a given role. Usage: {{ user|has_role:'doctor' }}"""
    if not user or not user.is_authenticated:
        return False
    return user.role == role


@register.filter(name='in_roles')
def in_roles(user, roles):
    """Check if user's role is in a list. Usage: {{ user|in_roles:'super_admin,doctor' }}"""
    if not user or not user.is_authenticated:
        return False
    allowed = [r.strip() for r in roles.split(',')]
    return user.role in allowed


@register.simple_tag(takes_context=True)
def role_menu_items(context):
    """Return role-specific menu items for the sidebar."""
    user = context.get('user')

    if not user or not user.is_authenticated:
        return []

    all_items = [
        {'name': 'Dashboard', 'icon': 'fas fa-chart-pie', 'url': 'analytics:dashboard', 'roles': '__all__'},
        {'name': 'Hospitals', 'icon': 'fas fa-hospital', 'url': 'hospitals:list', 'roles': ['super_admin']},
        {'name': 'Doctors', 'icon': 'fas fa-user-md', 'url': 'doctors:list', 'roles': ['super_admin', 'hospital_admin']},
        {'name': 'Patients', 'icon': 'fas fa-users', 'url': 'patients:list', 'roles': ['super_admin', 'hospital_admin', 'doctor', 'receptionist']},
        {'name': 'Appointments', 'icon': 'fas fa-calendar-check', 'url': 'appointments:list', 'roles': ['super_admin', 'hospital_admin', 'doctor', 'receptionist']},
        {'name': 'Medical Records', 'icon': 'fas fa-notes-medical', 'url': 'medical_records:record_list', 'roles': ['super_admin', 'hospital_admin', 'doctor']},
        {'name': 'Prescriptions', 'icon': 'fas fa-prescription-bottle', 'url': 'prescriptions:list', 'roles': ['super_admin', 'hospital_admin', 'doctor']},
        {'name': 'Laboratory', 'icon': 'fas fa-flask', 'url': 'laboratory:dashboard', 'roles': ['super_admin', 'hospital_admin', 'lab_technician']},
        {'name': 'Pharmacy', 'icon': 'fas fa-pills', 'url': 'pharmacy:dashboard', 'roles': ['super_admin', 'hospital_admin', 'pharmacist']},
        {'name': 'Analytics', 'icon': 'fas fa-chart-line', 'url': 'analytics:dashboard', 'roles': ['super_admin', 'hospital_admin']},
        {'name': 'Notifications', 'icon': 'fas fa-bell', 'url': 'notifications:center', 'roles': '__all__'},

        # Future Modules
        {'name': 'Reports', 'icon': 'fas fa-file-alt', 'url': 'analytics:reports', 'roles': ['super_admin']},
        {'name': 'Settings', 'icon': 'fas fa-cog', 'url': 'analytics:settings', 'roles': ['super_admin']},
    ]

    role = user.role

    return [
        item for item in all_items
        if item['roles'] == '__all__' or role in item['roles']
    ]


@register.simple_tag(takes_context=True)
def dashboard_widgets(context):
    """Return role-specific dashboard widgets."""
    user = context.get('user')

    if not user or not user.is_authenticated:
        return []

    widgets = {
        'super_admin': ['total_hospitals', 'total_doctors', 'total_patients', 'revenue', 'analytics', 'recent_activity'],
        'hospital_admin': ['total_doctors', 'total_patients', 'today_appointments', 'recent_activity'],
        'doctor': ['today_appointments', 'my_patients', 'pending_prescriptions', 'notifications'],
        'receptionist': ['today_queue', 'today_appointments', 'register_patient', 'notifications'],
        'lab_technician': ['pending_tests', 'completed_tests', 'today_reports'],
        'pharmacist': ['today_prescriptions', 'medicine_stock', 'low_stock_alert'],
        'patient': ['upcoming_appointment', 'prescriptions', 'medical_history', 'notifications'],
    }

    return widgets.get(user.role, [])