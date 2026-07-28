// appointments/static/appointments/js/appointment.js
/**
 * Appointment Module JavaScript
 * 
 * Provides interactive functionality for the appointment module:
 * - Live search with debounce
 * - AJAX status updates (confirm, cancel, complete)
 * - Confirmation dialogs for destructive actions
 * - Filter form enhancements
 * - Date picker integration (native with optional flatpickr)
 * 
 * @version 1.0.0
 * @author NHIMS Development Team
 */

(function() {
    'use strict';

    // ============================================
    // CONFIGURATION
    // ============================================
    const CONFIG = {
        SEARCH_DEBOUNCE_MS: 300,
        STATUS_ACTION_ENDPOINTS: {
            confirm: '/appointments/{id}/confirm/',
            cancel: '/appointments/{id}/cancel/',
            complete: '/appointments/{id}/complete/',
        },
        CSRF_TOKEN: document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
    };

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================
    const utils = {
        /**
         * Get CSRF token from cookie (fallback)
         */
        getCsrfToken: function() {
            if (CONFIG.CSRF_TOKEN) return CONFIG.CSRF_TOKEN;
            const cookieValue = document.cookie.match(/csrftoken=([^;]+)/);
            return cookieValue ? cookieValue[1] : '';
        },

        /**
         * Debounce function to limit rapid calls
         */
        debounce: function(func, delay) {
            let timeoutId;
            return function(...args) {
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => {
                    func.apply(this, args);
                }, delay);
            };
        },

        /**
         * Show a toast notification
         */
        showToast: function(message, type = 'success') {
            // Use Django messages or custom toast – we'll use a simple alert for now
            // You can replace with a beautiful toast library (e.g., notyf, toastr)
            // For production, we might dispatch a custom event or use Django messages.
            // If using Django messages, we need to reload to show them.
            // For AJAX, we can use a small toast container.
            const toastContainer = document.getElementById('toast-container');
            if (!toastContainer) {
                // Fallback: alert
                alert(message);
                return;
            }
            const toast = document.createElement('div');
            toast.className = `toast toast-${type} show`;
            toast.textContent = message;
            toastContainer.appendChild(toast);
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        },

        /**
         * Show confirmation dialog
         */
        confirmAction: function(message, callback) {
            if (confirm(message)) {
                callback();
            }
        },

        /**
         * Send AJAX request with Fetch API
         */
        fetchJSON: function(url, method = 'POST', data = null) {
            const headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCsrfToken(),
            };
            if (!(data instanceof FormData)) {
                headers['Content-Type'] = 'application/json';
            }
            const options = {
                method: method,
                headers: headers,
                credentials: 'same-origin',
            };
            if (data) {
                options.body = data instanceof FormData ? data : JSON.stringify(data);
            }
            return fetch(url, options).then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(text || 'Server error');
                    });
                }
                return response.json();
            });
        },
    };

    // ============================================
    // CORE MODULE
    // ============================================
    const AppointmentModule = {
        /**
         * Initialize all components
         */
        init: function() {
            this.initLiveSearch();
            this.initStatusButtons();
            this.initDeleteConfirmation();
            this.initFilterForm();
            this.initDatePickers();
            this.initAutoCompleteHelpers();
            this.initToastContainer();
        },

        /**
         * Create a toast container if not exists
         */
        initToastContainer: function() {
            if (!document.getElementById('toast-container')) {
                const container = document.createElement('div');
                container.id = 'toast-container';
                container.style.position = 'fixed';
                container.style.bottom = '20px';
                container.style.right = '20px';
                container.style.zIndex = '9999';
                document.body.appendChild(container);
            }
        },

        // ------------------------------------------
        // 1. Live Search (with debounce)
        // ------------------------------------------
        initLiveSearch: function() {
            const searchInput = document.getElementById('search-input') || document.querySelector('input[name="search"]');
            if (!searchInput) return;

            const debouncedSearch = utils.debounce(function() {
                const form = searchInput.closest('form');
                if (form) {
                    form.submit();
                } else {
                    // If no form, reload with query param
                    const url = new URL(window.location);
                    url.searchParams.set('search', searchInput.value);
                    window.location.href = url.toString();
                }
            }, CONFIG.SEARCH_DEBOUNCE_MS);

            searchInput.addEventListener('input', debouncedSearch);
        },

        // ------------------------------------------
        // 2. AJAX Status Buttons (Confirm, Cancel, Complete)
        // ------------------------------------------
        initStatusButtons: function() {
            document.querySelectorAll('[data-action="confirm"], [data-action="cancel"], [data-action="complete"]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const action = btn.dataset.action;
                    const appointmentId = btn.dataset.appointmentId;
                    const url = btn.dataset.url || `/appointments/${appointmentId}/${action}/`;
                    const confirmMessage = btn.dataset.confirmMessage || `Are you sure you want to ${action} this appointment?`;

                    // Show confirmation dialog if needed
                    const requiresConfirmation = btn.dataset.confirm === 'true';
                    if (requiresConfirmation) {
                        utils.confirmAction(confirmMessage, () => {
                            this.performStatusUpdate(url, action, btn);
                        });
                    } else {
                        this.performStatusUpdate(url, action, btn);
                    }
                });
            });
        },

        performStatusUpdate: function(url, action, button) {
            const originalHtml = button.innerHTML;
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';

            utils.fetchJSON(url, 'POST')
                .then(data => {
                    if (data.success) {
                        utils.showToast(data.message || `${action} successful!`, 'success');
                        // Reload page to reflect changes (or update DOM)
                        window.location.reload();
                    } else {
                        utils.showToast(data.message || `Failed to ${action} appointment`, 'error');
                        button.disabled = false;
                        button.innerHTML = originalHtml;
                    }
                })
                .catch(error => {
                    utils.showToast(`Error: ${error.message}`, 'error');
                    button.disabled = false;
                    button.innerHTML = originalHtml;
                });
        },

        // ------------------------------------------
        // 3. Delete Confirmation (for delete view)
        // ------------------------------------------
        initDeleteConfirmation: function() {
            const deleteForm = document.getElementById('delete-appointment-form');
            if (deleteForm) {
                deleteForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    const message = deleteForm.dataset.confirmMessage || 'Are you sure you want to permanently delete this appointment?';
                    utils.confirmAction(message, () => {
                        deleteForm.submit();
                    });
                });
            }
        },

        // ------------------------------------------
        // 4. Filter Form Enhancements (auto-submit on change)
        // ------------------------------------------
        initFilterForm: function() {
            const filterForm = document.getElementById('filter-form') || document.querySelector('.filter-bar form');
            if (!filterForm) return;

            // Auto-submit on select change
            const selects = filterForm.querySelectorAll('select');
            selects.forEach(select => {
                select.addEventListener('change', () => {
                    filterForm.submit();
                });
            });

            // Submit on date change
            const dateInputs = filterForm.querySelectorAll('input[type="date"]');
            dateInputs.forEach(input => {
                input.addEventListener('change', () => {
                    filterForm.submit();
                });
            });

            // Preserve search input behavior (already handled by live search)
            const searchInput = filterForm.querySelector('input[name="search"]');
            if (searchInput) {
                // Remove default form submission on enter (we use debounced)
                searchInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        filterForm.submit();
                    }
                });
            }
        },

        // ------------------------------------------
        // 5. Date Picker Enhancement (native with flatpickr fallback)
        // ------------------------------------------
        initDatePickers: function() {
            // Use native date inputs – but if flatpickr is available, enhance.
            // Check if flatpickr is loaded.
            if (typeof flatpickr !== 'undefined') {
                const dateInputs = document.querySelectorAll('input[type="date"]');
                dateInputs.forEach(input => {
                    flatpickr(input, {
                        dateFormat: 'Y-m-d',
                        allowInput: true,
                        weekNumbers: true,
                        // Additional options
                    });
                });
            } else {
                // Native date inputs already work; add some styling if needed.
                // Optionally, we could add a simple date picker polyfill.
            }
        },

        // ------------------------------------------
        // 6. Auto-complete helpers (if using select2 or chosen)
        // ------------------------------------------
        initAutoCompleteHelpers: function() {
            // If we use select2 for doctor/patient/hospital dropdowns, init here.
            // For now, we keep native selects with search (HTML5 datalist maybe)
            // We'll add a fallback for better UX:
            const selects = document.querySelectorAll('select[data-live-search="true"]');
            // You can implement a simple filterable select if needed.
            // For production, consider using a lightweight library.
        },
    };

    // ============================================
    // INITIALIZATION
    // ============================================
    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => AppointmentModule.init());
    } else {
        AppointmentModule.init();
    }

    // ============================================
    // EXPOSE MODULE (for debugging or testing)
    // ============================================
    window.AppointmentModule = AppointmentModule;

})();