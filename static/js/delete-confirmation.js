// Add this to a new file: static/js/delete-confirmation.js
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('deleteConfirmationModal');
    const cancelButton = document.getElementById('cancelDelete');
    const confirmButton = document.getElementById('confirmDelete');
    let deleteUrl = '';

    // Function to show modal
    function showDeleteModal(url) {
        deleteUrl = url;
        modal.classList.remove('hidden');
    }

    // Function to hide modal
    function hideDeleteModal() {
        modal.classList.add('hidden');
        deleteUrl = '';
    }

    // Handle delete button clicks
    document.querySelectorAll('.delete-expense-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            showDeleteModal(this.getAttribute('href'));
        });
    });

    // Handle cancel button
    cancelButton.addEventListener('click', hideDeleteModal);

    // Handle confirm delete
    confirmButton.addEventListener('click', function() {
        if (deleteUrl) {
            window.location.href = deleteUrl;
        }
    });

    // Close modal when clicking outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            hideDeleteModal();
        }
    });

    // Close modal on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
            hideDeleteModal();
        }
    });
});