// Gestion des messages Django avec SweetAlert2
document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si SweetAlert2 est chargé
    if (typeof Swal === 'undefined') {
        console.warn('SweetAlert2 n\'est pas chargé. Les messages seront affichés avec les alertes par défaut.');
        return;
    }

    // Fonction pour afficher les messages Django
    function showDjangoMessages() {
        // Récupérer tous les messages Django
        const messages = document.querySelectorAll('.messages .alert, .alert-dismissible');
        
        messages.forEach(function(message) {
            // Déterminer le type de message
            let type = 'info';
            if (message.classList.contains('alert-success')) {
                type = 'success';
            } else if (message.classList.contains('alert-danger')) {
                type = 'error';
            } else if (message.classList.contains('alert-warning')) {
                type = 'warning';
            }

            // Récupérer le texte du message
            const title = type.charAt(0).toUpperCase() + type.slice(1);
            const text = message.textContent.trim();

            // Afficher avec SweetAlert2
            Swal.fire({
                title: title,
                text: text,
                icon: type,
                confirmButtonText: 'OK',
                timer: 5000,
                timerProgressBar: true,
                toast: false,
                position: 'center'
            });

            // Supprimer le message original
            message.style.display = 'none';
        });
    }

    // Fonction pour gérer les messages dans les formulaires
    function handleFormMessages() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(function(form) {
            form.addEventListener('submit', function(e) {
                const submitButton = form.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> En cours...';
                }
            });
        });
    }

    // Appeler les fonctions d'initialisation
    showDjangoMessages();
    handleFormMessages();
});
