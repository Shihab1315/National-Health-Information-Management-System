# Constants used across the analytics app.
# These values are shared between services, views, and templates.

# Role names (for permission checks)
ROLE_ADMIN = 'admin'
ROLE_DOCTOR = 'doctor'
ROLE_HOSPITAL_ADMIN = 'hospital_admin'
ROLE_LAB_TECHNICIAN = 'lab_technician'
ROLE_PHARMACIST = 'pharmacist'
ROLE_PATIENT = 'patient'

# Allowed roles for the analytics dashboard
ALLOWED_ROLES = [ROLE_ADMIN, ROLE_DOCTOR, ROLE_HOSPITAL_ADMIN, ROLE_LAB_TECHNICIAN, ROLE_PHARMACIST]

# Chart default colors (tailwind-style palette)
CHART_COLORS = {
    'blue': '#3b82f6',
    'emerald': '#10b981',
    'amber': '#f59e0b',
    'red': '#ef4444',
    'purple': '#8b5cf6',
    'cyan': '#06b6d4',
    'pink': '#ec4899',
    'indigo': '#6366f1',
    'gray': '#6b7280',
}

# Status badge color mapping (for consistent display)
STATUS_COLORS = {
    'pending': 'amber',
    'confirmed': 'blue',
    'completed': 'emerald',
    'cancelled': 'red',
    'active': 'blue',
    'draft': 'gray',
    'published': 'emerald',
    'verified': 'cyan',
    'cancelled': 'red',
    'expired': 'gray',
}

# Duration for caching dashboard data (in seconds)
CACHE_TIMEOUT = 60 * 5  # 5 minutes

# Number of items to display in "recent" lists
RECENT_LIMIT = 5

# Default date range for chart data (in days)
CHART_DAYS_BACK = 180  # roughly 6 months