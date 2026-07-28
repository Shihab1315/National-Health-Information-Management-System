// appointment_create.js

(function() {
  'use strict';

  // ===== DOM READY =====
  document.addEventListener('DOMContentLoaded', function() {

    // ---------- 1. Initialize Select2 on all dropdowns ----------
    const selectElements = document.querySelectorAll('select:not([multiple])');
    selectElements.forEach(select => {
      // Skip if already initialized
      if ($(select).data('select2')) return;
      $(select).select2({
        theme: 'bootstrap-5',
        width: '100%',
        placeholder: $(select).data('placeholder') || 'Select an option',
        allowClear: true
      });
    });

    // ---------- 2. Initialize Flatpickr (Date & Time) ----------
    // Date picker
    const dateInput = document.getElementById('{{ form.appointment_date.id_for_label }}');
    if (dateInput) {
      flatpickr(dateInput, {
        minDate: 'today',
        dateFormat: 'Y-m-d',
        disableMobile: true,
        onChange: function(selectedDates, dateStr) {
          // Trigger validation
          validateField(dateInput);
        }
      });
    }

    // Time picker with 15-min intervals
    const timeInput = document.getElementById('{{ form.appointment_time.id_for_label }}');
    if (timeInput) {
      flatpickr(timeInput, {
        enableTime: true,
        noCalendar: true,
        dateFormat: 'H:i',
        minuteIncrement: 15,
        disableMobile: true,
        onChange: function(selectedDates, timeStr) {
          validateField(timeInput);
        }
      });
    }

    // ---------- 3. Dynamic Doctor Loading (AJAX) ----------
    const hospitalSelect = document.getElementById('{{ form.hospital.id_for_label }}');
    const doctorSelect = document.getElementById('{{ form.doctor.id_for_label }}');

    if (hospitalSelect && doctorSelect) {
      hospitalSelect.addEventListener('change', function() {
        const hospitalId = this.value;
        if (!hospitalId) {
          // Clear doctor dropdown and reset
          $(doctorSelect).empty().trigger('change');
          return;
        }

        // Show loading state
        $(doctorSelect).prop('disabled', true);
        $(doctorSelect).append('<option value="" disabled>Loading doctors...</option>');

        // AJAX call to fetch doctors
        fetch(`/api/doctors-by-hospital/?hospital_id=${hospitalId}`)
          .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
          })
          .then(data => {
            // Clear existing options (keep placeholder)
            $(doctorSelect).empty();
            // Add default option
            $(doctorSelect).append('<option value="">Select Doctor</option>');
            // Add fetched doctors
            if (data.doctors && data.doctors.length) {
              data.doctors.forEach(doc => {
                $(doctorSelect).append(`<option value="${doc.id}">${doc.name}</option>`);
              });
            } else {
              $(doctorSelect).append('<option value="" disabled>No doctors available</option>');
            }
            // Refresh Select2
            $(doctorSelect).trigger('change');
            $(doctorSelect).prop('disabled', false);
          })
          .catch(error => {
            console.error('Error loading doctors:', error);
            $(doctorSelect).empty();
            $(doctorSelect).append('<option value="" disabled>Error loading doctors</option>');
            $(doctorSelect).trigger('change');
            $(doctorSelect).prop('disabled', false);
            showToast('Failed to load doctors', 'error');
          });
      });
    }

    // ---------- 4. Form Validation (Bootstrap) ----------
    const form = document.getElementById('appointmentForm');

    // Add validation on blur for fields
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
      // Skip readonly fields
      if (input.readOnly) return;
      input.addEventListener('blur', function() {
        validateField(this);
      });
      // Also validate on change for selects
      if (input.tagName === 'SELECT') {
        input.addEventListener('change', function() {
          validateField(this);
        });
      }
    });

    // Function to validate a single field
    function validateField(field) {
      // Remove existing validation classes
      field.classList.remove('is-valid', 'is-invalid');
      const feedback = field.closest('.input-group')
        ? field.closest('.input-group').parentElement.querySelector('.invalid-feedback')
        : field.parentElement.querySelector('.invalid-feedback');

      if (!feedback) return;

      if (field.validity.valid) {
        field.classList.add('is-valid');
        feedback.textContent = '';
      } else {
        field.classList.add('is-invalid');
        feedback.textContent = field.validationMessage || 'Invalid value';
      }
    }

    // ---------- 5. Form Submission (with spinner & disable) ----------
    form.addEventListener('submit', function(e) {
      // Prevent default if client-side validation fails
      if (!form.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
        // Show all invalid fields
        form.querySelectorAll('input, select, textarea').forEach(field => {
          if (!field.validity.valid && !field.readOnly) {
            field.classList.add('is-invalid');
          }
        });
        showToast('Please correct the highlighted fields.', 'error');
        return;
      }

      // Disable button and show spinner
      const submitBtn = document.getElementById('submitBtn');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

      // Allow form to submit naturally (server-side validation)
      // We'll let the server handle errors; if there's a server error, we'll show it via messages.
      // After submission, the page will reload.
    });

    // ---------- 6. Toast Notification (custom) ----------
    function showToast(message, type = 'success') {
      // Use Bootstrap toast if available, else fallback to alert
      const toastContainer = document.getElementById('toastContainer');
      if (toastContainer) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : 'success'} border-0 show`;
        toast.role = 'alert';
        toast.innerHTML = `
          <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
          </div>
        `;
        toastContainer.appendChild(toast);
        setTimeout(() => {
          toast.classList.remove('show');
          setTimeout(() => toast.remove(), 300);
        }, 4000);
      } else {
        alert(message);
      }
    }

    // ---------- 7. Confirmation dialog for cancel (optional) ----------
    const cancelBtn = document.querySelector('a[href*="appointments:list"]');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', function(e) {
        if (!confirm('Are you sure you want to cancel? Unsaved changes will be lost.')) {
          e.preventDefault();
        }
      });
    }

    // ---------- 8. Auto-resize textareas ----------
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(ta => {
      ta.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
      });
      // Initial resize
      setTimeout(() => {
        ta.style.height = 'auto';
        ta.style.height = ta.scrollHeight + 'px';
      }, 100);
    });

  });
})();