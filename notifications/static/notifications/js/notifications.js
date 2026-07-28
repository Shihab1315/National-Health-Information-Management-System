document.addEventListener('DOMContentLoaded', function() {

    // ---- Mark single notification as read ----
    document.querySelectorAll('.mark-read-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const card = this.closest('.notification-card');
            const pk = card.dataset.notificationId;
            fetch(`/notifications/mark-read/${pk}/`, { method: 'POST', headers: { 'X-CSRFToken': getCSRFToken() } })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'ok') {
                        card.classList.remove('border-l-4', 'border-blue-500');
                        card.querySelector('.mark-read-btn')?.remove();
                        // Update unread badge
                        updateBadge();
                    }
                });
        });
    });

    // ---- Delete single notification ----
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            if (!confirm('Delete this notification?')) return;
            const card = this.closest('.notification-card');
            const pk = card.dataset.notificationId;
            fetch(`/notifications/delete/${pk}/`, { method: 'POST', headers: { 'X-CSRFToken': getCSRFToken() } })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'ok') {
                        card.remove();
                        updateBadge();
                    }
                });
        });
    });

    // ---- Mark all read (main page) ----
    document.getElementById('mark-all-read-btn')?.addEventListener('click', function(e) {
        e.preventDefault();
        fetch('/notifications/mark-all-read/', { method: 'POST', headers: { 'X-CSRFToken': getCSRFToken() } })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'ok') {
                    location.reload();
                }
            });
    });

    // ---- Delete all read (main page) ----
    document.getElementById('delete-all-read-btn')?.addEventListener('click', function(e) {
        e.preventDefault();
        if (!confirm('Delete all read notifications?')) return;
        fetch('/notifications/delete-all-read/', { method: 'POST', headers: { 'X-CSRFToken': getCSRFToken() } })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'ok') {
                    location.reload();
                }
            });
    });

    // ---- Click on card to go to detail (if url present) ----
    window.handleCardClick = function(event, card) {
        // Ignore if click was on a button or link inside
        if (event.target.closest('button') || event.target.closest('a')) return;
        const url = card.querySelector('a[href]')?.getAttribute('href');
        if (url) {
            window.location.href = url;
        }
    };

    // ---- Update unread badge (polling + after actions) ----
    function updateBadge() {
        fetch('/notifications/unread-count/')
            .then(res => res.json())
            .then(data => {
                const count = data.count || 0;
                const display = document.getElementById('unread-count-display');
                const badge = document.getElementById('unread-badge');
                if (display) {
                    display.textContent = count;
                    display.classList.remove('pulse');
                    // Trigger pulse animation
                    void display.offsetWidth;
                    display.classList.add('pulse');
                }
                if (badge) {
                    badge.textContent = count > 99 ? '99+' : count;
                    badge.style.display = count > 0 ? 'flex' : 'none';
                }
            });
    }

    // ---- Polling every 30 seconds ----
    setInterval(() => {
        updateBadge();
    }, 30000);

    // ---- CSRF helper ----
    function getCSRFToken() {
        const cookieValue = document.cookie.split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    // ---- Auto-submit toolbar on select change ----
   const filterForm = document.getElementById('notification-filter-form');

document.querySelectorAll(
'#notification-toolbar select,#notification-toolbar input'
).forEach(el=>{

    el.addEventListener('change',function(){

        if(filterForm){
            filterForm.submit();
        }

    });

});
});