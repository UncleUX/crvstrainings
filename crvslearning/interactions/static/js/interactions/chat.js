// Configuration globale
const config = {
    // URL de l'API WebSocket (à remplacer par votre configuration)
    wsUrl: `ws://${window.location.host}/ws/chat/`,
    // URL de base de l'API
    apiBaseUrl: '/api',
    // Durée d'affichage des notifications toast (en ms)
    toastDuration: 5000,
};

// État global de l'application
const state = {
    // Connexion WebSocket
    socket: null,
    // ID de la salle de discussion actuelle
    currentRoomId: null,
    // ID de l'utilisateur connecté
    currentUserId: document.body.dataset.userId || null,
    // État de frappe
    isTyping: false,
    // Dernier ID de message reçu
    lastMessageId: null,
    // Délai avant envoi de l'état de frappe (en ms)
    typingTimeout: null,
    // Délai avant arrêt de l'état de frappe (en ms)
    stopTypingTimeout: null,
    // Fichiers à envoyer
    filesToUpload: [],
};

// Initialisation de l'application
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser la connexion WebSocket
    initWebSocket();
    
    // Gestion de l'envoi de messages
    const messageForm = document.getElementById('message-form');
    if (messageForm) {
        messageForm.addEventListener('submit', handleMessageSubmit);
        
        // Gestion de la frappe
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.addEventListener('input', handleTyping);
            messageInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    messageForm.dispatchEvent(new Event('submit'));
                }
            });
        }
        
        // Gestion des pièces jointes
        const attachFileBtn = document.getElementById('attach-file-btn');
        const fileUpload = document.getElementById('file-upload');
        
        if (attachFileBtn && fileUpload) {
            attachFileBtn.addEventListener('click', () => fileUpload.click());
            fileUpload.addEventListener('change', handleFileSelect);
        }
    }
    
    // Gestion des notifications
    setupNotificationHandlers();
    
    // Charger les conversations
    loadConversations();
    
    // Configurer les tooltips Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Configurer les popovers Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Gestion du mode mobile
    setupMobileHandlers();
});

// Initialisation de la connexion WebSocket
function initWebSocket() {
    if (state.currentUserId) {
        try {
            state.socket = new WebSocket(`${config.wsUrl}${state.currentUserId}/`);
            
            state.socket.onopen = function(e) {
                console.log('WebSocket connection established');
                // S'abonner aux mises à jour en temps réel
                subscribeToUpdates();
            };
            
            state.socket.onmessage = function(e) {
                const data = JSON.parse(e.data);
                handleWebSocketMessage(data);
            };
            
            state.socket.onclose = function(e) {
                console.log('WebSocket connection closed. Attempting to reconnect...');
                // Tentative de reconnexion après un délai
                setTimeout(initWebSocket, 5000);
            };
            
            state.socket.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
        }
    }
}

// S'abonner aux mises à jour en temps réel
function subscribeToUpdates() {
    if (state.socket && state.socket.readyState === WebSocket.OPEN) {
        state.socket.send(JSON.stringify({
            'type': 'subscribe',
            'user_id': state.currentUserId
        }));
    }
}

// Gérer les messages WebSocket entrants
function handleWebSocketMessage(data) {
    console.log('WebSocket message received:', data);
    
    switch (data.type) {
        case 'chat_message':
            handleIncomingMessage(data);
            break;
            
        case 'typing':
            handleTypingIndicator(data);
            break;
            
        case 'message_read':
            handleMessageRead(data);
            break;
            
        case 'notification':
            handleNewNotification(data);
            break;
            
        case 'user_status':
            updateUserStatus(data);
            break;
            
        default:
            console.warn('Unknown message type:', data.type);
    }
}

// Gérer l'envoi d'un message
async function handleMessageSubmit(e) {
    e.preventDefault();
    
    const messageInput = document.getElementById('message-input');
    const messageText = messageInput.value.trim();
    
    // Vérifier si le message est vide et qu'il n'y a pas de fichiers à envoyer
    if (!messageText && state.filesToUpload.length === 0) {
        return;
    }
    
    // Désactiver le bouton d'envoi pendant le traitement
    const sendButton = document.getElementById('send-message-btn');
    const originalButtonContent = sendButton.innerHTML;
    sendButton.disabled = true;
    sendButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
    
    try {
        // Préparer les données du formulaire
        const formData = new FormData();
        
        // Ajouter le texte du message s'il y en a un
        if (messageText) {
            formData.append('message', messageText);
        }
        
        // Ajouter les fichiers s'il y en a
        state.filesToUpload.forEach((file, index) => {
            formData.append(`file_${index}`, file);
        });
        
        // Envoyer le message via l'API
        const response = await fetch(`${config.apiBaseUrl}/messages/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: formData,
        });
        
        if (!response.ok) {
            throw new Error('Failed to send message');
        }
        
        const result = await response.json();
        
        // Réinitialiser le champ de saisie et la prévisualisation des pièces jointes
        messageInput.value = '';
        resetFilePreview();
        
        // Faire défiler vers le bas pour afficher le nouveau message
        scrollToBottom();
        
    } catch (error) {
        console.error('Error sending message:', error);
        showToast('Erreur', 'Impossible d\'envoyer le message. Veuillez réessayer.', 'error');
    } finally {
        // Réactiver le bouton d'envoi
        sendButton.disabled = false;
        sendButton.innerHTML = originalButtonContent;
    }
    
    // Réinitialiser l'état de frappe
    resetTyping();
}

// Gérer la réception d'un nouveau message
function handleIncomingMessage(data) {
    // Vérifier si le message est pour la conversation actuelle
    const isCurrentConversation = state.currentRoomId === data.room_id;
    
    // Mettre à jour l'interface utilisateur
    if (isCurrentConversation) {
        // Ajouter le message à la conversation
        appendMessage(data);
        
        // Mettre à jour le dernier message dans la liste des conversations
        updateConversationPreview(data);
        
        // Marquer le message comme lu
        markMessageAsRead(data.id);
    } else {
        // Mettre à jour le badge de notification
        updateUnreadCount(1);
        
        // Mettre à jour la prévisualisation de la conversation
        updateConversationPreview(data);
        
        // Afficher une notification toast
        if (document.hidden) {
            showNotification(data.sender_name, data.message, data.sender_avatar);
        }
    }
}

// Ajouter un message à la conversation
function appendMessage(message) {
    const messagesContainer = document.getElementById('chat-messages');
    
    // Créer l'élément du message
    const messageElement = document.createElement('div');
    messageElement.className = `message ${message.sender_id === state.currentUserId ? 'sent' : 'received'}`;
    messageElement.dataset.messageId = message.id;
    
    // Formater l'heure
    const messageTime = new Date(message.timestamp);
    const formattedTime = messageTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    // Construire le HTML du message
    let messageHtml = `
        <div class="message-content">
            ${message.sender_id !== state.currentUserId ? 
                `<div class="message-sender">${message.sender_name}</div>` : ''
            }
            <div class="message-text">
                ${formatMessageContent(message.content)}
                <div class="message-time">
                    ${formattedTime}
                    ${message.sender_id === state.currentUserId ? 
                        `<i class="fas ${message.read ? 'fa-check-double text-primary' : 'fa-check'}"></i>` : ''
                    }
                </div>
            </div>
        </div>
    `;
    
    // Ajouter l'avatar pour les messages reçus
    if (message.sender_id !== state.currentUserId) {
        messageHtml = `
            <div class="message-avatar">
                ${message.sender_avatar ? 
                    `<img src="${message.sender_avatar}" alt="${message.sender_name}">` :
                    `<div class="avatar-placeholder">
                        ${getInitials(message.sender_name)}
                    </div>`
                }
            </div>
        ` + messageHtml;
    }
    
    messageElement.innerHTML = messageHtml;
    
    // Ajouter le message au conteneur
    messagesContainer.appendChild(messageElement);
    
    // Faire défiler vers le bas pour afficher le nouveau message
    scrollToBottom();
}

// Formater le contenu du message (liens, sauts de ligne, etc.)
function formatMessageContent(content) {
    if (!content) return '';
    
    // Remplacer les sauts de ligne par des balises <br>
    let formattedContent = content.replace(/\n/g, '<br>');
    
    // Mettre en surbrillance les mentions
    formattedContent = formattedContent.replace(/@(\w+)/g, '<span class="mention">@$1</span>');
    
    // Détecter et créer des liens cliquables
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    formattedContent = formattedContent.replace(urlRegex, function(url) {
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
    });
    
    return formattedContent;
}

// Obtenir les initiales d'un nom
function getInitials(name) {
    if (!name) return '';
    
    return name
        .split(' ')
        .map(part => part[0])
        .join('')
        .toUpperCase()
        .substring(0, 2);
}

// Faire défiler vers le bas du conteneur des messages
function scrollToBottom() {
    const messagesContainer = document.getElementById('chat-messages');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Gérer l'indicateur de frappe
function handleTyping() {
    const messageInput = document.getElementById('message-input');
    
    // Ne pas envoyer l'état de frappe si le champ est vide
    if (!messageInput.value.trim()) {
        resetTyping();
        return;
    }
    
    // Envoyer l'état de frappe si ce n'est pas déjà fait
    if (!state.isTyping) {
        state.isTyping = true;
        sendTypingStatus(true);
    }
    
    // Réinitialiser le délai d'arrêt de la frappe
    clearTimeout(state.typingTimeout);
    state.typingTimeout = setTimeout(resetTyping, 2000);
}

// Réinitialiser l'état de frappe
function resetTyping() {
    if (state.isTyping) {
        state.isTyping = false;
        sendTypingStatus(false);
    }
    
    clearTimeout(state.typingTimeout);
}

// Envoyer l'état de frappe au serveur
function sendTypingStatus(isTyping) {
    if (state.socket && state.socket.readyState === WebSocket.OPEN && state.currentRoomId) {
        state.socket.send(JSON.stringify({
            'type': 'typing',
            'room_id': state.currentRoomId,
            'is_typing': isTyping,
            'user_id': state.currentUserId
        }));
    }
}

// Gérer l'affichage de l'indicateur de frappe
function handleTypingIndicator(data) {
    if (data.room_id !== state.currentRoomId || data.user_id === state.currentUserId) {
        return;
    }
    
    const typingIndicator = document.getElementById('typing-indicator');
    if (!typingIndicator) return;
    
    if (data.is_typing) {
        typingIndicator.innerHTML = `
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <span>${data.user_name} est en train d'écrire...</span>
        `;
        typingIndicator.style.display = 'flex';
        
        // Masquer l'indicateur après 3 secondes
        clearTimeout(state.stopTypingTimeout);
        state.stopTypingTimeout = setTimeout(() => {
            typingIndicator.style.display = 'none';
        }, 3000);
    } else {
        typingIndicator.style.display = 'none';
    }
}

// Marquer un message comme lu
function markMessageAsRead(messageId) {
    if (!messageId) return;
    
    fetch(`${config.apiBaseUrl}/messages/${messageId}/read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to mark message as read');
        }
        return response.json();
    })
    .then(data => {
        // Mettre à jour l'interface utilisateur
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageElement) {
            const checkIcon = messageElement.querySelector('.fa-check');
            if (checkIcon) {
                checkIcon.classList.remove('fa-check');
                checkIcon.classList.add('fa-check-double', 'text-primary');
            }
        }
    })
    .catch(error => {
        console.error('Error marking message as read:', error);
    });
}

// Mettre à jour la prévisualisation d'une conversation
function updateConversationPreview(message) {
    const conversationItem = document.querySelector(`[data-conversation-id="${message.room_id}"]`);
    
    if (conversationItem) {
        // Mettre à jour le dernier message
        const previewElement = conversationItem.querySelector('.conversation-preview');
        if (previewElement) {
            const senderPrefix = message.sender_id === state.currentUserId ? 'Vous: ' : '';
            previewElement.textContent = senderPrefix + message.content.substring(0, 50);
            if (message.content.length > 50) {
                previewElement.textContent += '...';
            }
        }
        
        // Mettre à jour l'heure
        const timeElement = conversationItem.querySelector('.conversation-time');
        if (timeElement) {
            const messageTime = new Date(message.timestamp);
            timeElement.textContent = formatTimeAgo(messageTime);
        }
        
        // Mettre à jour le badge de notification si nécessaire
        if (message.sender_id !== state.currentUserId) {
            const unreadBadge = conversationItem.querySelector('.unread-badge');
            if (unreadBadge) {
                const currentCount = parseInt(unreadBadge.textContent) || 0;
                unreadBadge.textContent = currentCount + 1;
                unreadBadge.style.display = 'flex';
            } else {
                const badge = document.createElement('span');
                badge.className = 'unread-badge';
                badge.textContent = '1';
                conversationItem.querySelector('.conversation-avatar').appendChild(badge);
            }
        }
        
        // Déplacer la conversation en haut de la liste
        const conversationList = document.querySelector('.conversation-list');
        if (conversationList && conversationItem !== conversationList.firstElementChild) {
            conversationList.insertBefore(conversationItem, conversationList.firstChild);
        }
    }
}

// Formater la date en format relatif (il y a...)
function formatTimeAgo(date) {
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) {
        return 'À l\'instant';
    }
    
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) {
        return `Il y a ${diffInMinutes} min`;
    }
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) {
        return `Il y a ${diffInHours} h`;
    }
    
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) {
        return `Il y a ${diffInDays} j`;
    }
    
    // Pour les dates plus anciennes, afficher la date complète
    return date.toLocaleDateString();
}

// Mettre à jour le compteur de messages non lus
function updateUnreadCount(change) {
    const unreadCountElement = document.getElementById('unread-count');
    if (!unreadCountElement) return;
    
    let currentCount = parseInt(unreadCountElement.textContent) || 0;
    
    if (change === 'all') {
        currentCount = 0;
    } else {
        currentCount = Math.max(0, currentCount + change);
    }
    
    unreadCountElement.textContent = currentCount > 0 ? currentCount : '';
    unreadCountElement.style.display = currentCount > 0 ? 'flex' : 'none';
}

// Charger les conversations
function loadConversations() {
    fetch(`${config.apiBaseUrl}/conversations/`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to load conversations');
        }
        return response.json();
    })
    .then(conversations => {
        const conversationList = document.querySelector('.conversation-list');
        if (!conversationList) return;
        
        // Vider la liste actuelle
        conversationList.innerHTML = '';
        
        if (conversations.length === 0) {
            conversationList.innerHTML = `
                <div class="empty-state">
                    <i class="far fa-comment-dots"></i>
                    <p>{% trans "Aucune conversation" %}</p>
                    <small>{% trans "Commencez une nouvelle conversation pour voir les messages ici." %}</small>
                </div>
            `;
            return;
        }
        
        // Ajouter chaque conversation à la liste
        conversations.forEach(conversation => {
            const lastMessage = conversation.last_message || {};
            const otherUser = conversation.participants.find(p => p.id !== state.currentUserId) || {};
            
            const conversationElement = document.createElement('a');
            conversationElement.href = `#`;
            conversationElement.className = `conversation-item ${conversation.is_active ? 'active' : ''}`;
            conversationElement.dataset.conversationId = conversation.id;
            
            conversationElement.innerHTML = `
                <div class="conversation-avatar">
                    ${otherUser.avatar ? 
                        `<img src="${otherUser.avatar}" alt="${otherUser.name}">` :
                        `<div class="avatar-placeholder">${getInitials(otherUser.name)}</div>`
                    }
                    ${conversation.unread_count > 0 ? 
                        `<span class="unread-badge">${conversation.unread_count}</span>` : ''
                    }
                </div>
                <div class="conversation-details">
                    <div class="conversation-header">
                        <h4>${otherUser.name || 'Utilisateur inconnu'}</h4>
                        <span class="conversation-time">${formatTimeAgo(new Date(conversation.updated_at))}</span>
                    </div>
                    <p class="conversation-preview">
                        ${lastMessage.sender_id === state.currentUserId ? 'Vous: ' : ''}
                        ${lastMessage.content ? lastMessage.content.substring(0, 30) : 'Aucun message'}
                        ${lastMessage.content && lastMessage.content.length > 30 ? '...' : ''}
                    </p>
                </div>
            `;
            
            // Ajouter un gestionnaire d'événements pour sélectionner la conversation
            conversationElement.addEventListener('click', (e) => {
                e.preventDefault();
                selectConversation(conversation.id);
            });
            
            conversationList.appendChild(conversationElement);
        });
        
        // Sélectionner la première conversation par défaut
        if (conversations.length > 0) {
            selectConversation(conversations[0].id);
        }
    })
    .catch(error => {
        console.error('Error loading conversations:', error);
        showToast('Erreur', 'Impossible de charger les conversations', 'error');
    });
}

// Sélectionner une conversation
function selectConversation(conversationId) {
    // Mettre à jour l'interface utilisateur
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.toggle('active', item.dataset.conversationId === conversationId);
    });
    
    // Mettre à jour l'état actuel
    state.currentRoomId = conversationId;
    
    // Charger les messages de la conversation
    loadMessages(conversationId);
    
    // Marquer les messages comme lus
    markConversationAsRead(conversationId);
    
    // Mettre à jour l'URL
    history.pushState({}, '', `?conversation=${conversationId}`);
}

// Charger les messages d'une conversation
function loadMessages(conversationId) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    // Afficher un indicateur de chargement
    messagesContainer.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Chargement...</span>
            </div>
        </div>
    `;
    
    fetch(`${config.apiBaseUrl}/conversations/${conversationId}/messages/`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to load messages');
        }
        return response.json();
    })
    .then(messages => {
        // Vider le conteneur de messages
        messagesContainer.innerHTML = '';
        
        if (messages.length === 0) {
            messagesContainer.innerHTML = `
                <div class="empty-state">
                    <i class="far fa-comment-dots"></i>
                    <p>{% trans "Aucun message" %}</p>
                    <small>{% trans "Envoyez votre premier message pour commencer la conversation." %}</small>
                </div>
            `;
            return;
        }
        
        // Ajouter chaque message au conteneur
        messages.forEach(message => {
            appendMessage(message);
        });
        
        // Faire défiler vers le bas pour afficher le dernier message
        scrollToBottom();
        
        // Mettre à jour le dernier ID de message
        if (messages.length > 0) {
            state.lastMessageId = messages[messages.length - 1].id;
        }
    })
    .catch(error => {
        console.error('Error loading messages:', error);
        messagesContainer.innerHTML = `
            <div class="alert alert-danger" role="alert">
                Impossible de charger les messages. Veuillez réessayer.
            </div>
        `;
    });
}

// Marquer une conversation comme lue
function markConversationAsRead(conversationId) {
    fetch(`${config.apiBaseUrl}/conversations/${conversationId}/read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to mark conversation as read');
        }
        
        // Mettre à jour l'interface utilisateur
        const conversationItem = document.querySelector(`[data-conversation-id="${conversationId}"]`);
        if (conversationItem) {
            const unreadBadge = conversationItem.querySelector('.unread-badge');
            if (unreadBadge) {
                unreadBadge.remove();
            }
        }
        
        // Mettre à jour le compteur de messages non lus
        updateUnreadCount('all');
    })
    .catch(error => {
        console.error('Error marking conversation as read:', error);
    });
}

// Gérer la sélection de fichiers
function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    const previewContainer = document.getElementById('preview-attachments');
    
    if (!previewContainer) return;
    
    // Réinitialiser la prévisualisation
    resetFilePreview();
    
    // Vérifier le nombre de fichiers
    if (files.length > 5) {
        showToast('Erreur', 'Vous ne pouvez pas télécharger plus de 5 fichiers à la fois', 'error');
        return;
    }
    
    // Vérifier la taille totale des fichiers (max 10 Mo)
    const totalSize = files.reduce((total, file) => total + file.size, 0);
    if (totalSize > 10 * 1024 * 1024) {
        showToast('Erreur', 'La taille totale des fichiers ne doit pas dépasser 10 Mo', 'error');
        return;
    }
    
    // Stocker les fichiers pour l'envoi
    state.filesToUpload = files;
    
    // Afficher la prévisualisation des fichiers
    files.forEach(file => {
        const fileElement = document.createElement('div');
        fileElement.className = 'file-preview';
        
        // Vérifier le type de fichier
        if (file.type.startsWith('image/')) {
            // Aperçu pour les images
            const reader = new FileReader();
            reader.onload = function(e) {
                fileElement.innerHTML = `
                    <img src="${e.target.result}" alt="${file.name}" class="img-thumbnail">
                    <button type="button" class="btn-close" aria-label="Supprimer"></button>
                    <div class="file-info">
                        <span class="file-name">${file.name}</span>
                        <span class="file-size">${formatFileSize(file.size)}</span>
                    </div>
                `;
                
                // Ajouter un gestionnaire d'événements pour le bouton de suppression
                const removeButton = fileElement.querySelector('.btn-close');
                if (removeButton) {
                    removeButton.addEventListener('click', () => {
                        removeFile(file.name);
                        fileElement.remove();
                    });
                }
            };
            reader.readAsDataURL(file);
        } else {
            // Aperçu pour les autres types de fichiers
            const fileIcon = getFileIcon(file);
            fileElement.innerHTML = `
                <div class="file-icon">
                    <i class="${fileIcon}"></i>
                </div>
                <div class="file-info">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${formatFileSize(file.size)}</span>
                </div>
                <button type="button" class="btn-close" aria-label="Supprimer"></button>
            `;
            
            // Ajouter un gestionnaire d'événements pour le bouton de suppression
            const removeButton = fileElement.querySelector('.btn-close');
            if (removeButton) {
                removeButton.addEventListener('click', () => {
                    removeFile(file.name);
                    fileElement.remove();
                });
            }
        }
        
        previewContainer.appendChild(fileElement);
    });
    
    // Afficher le conteneur de prévisualisation
    previewContainer.style.display = 'flex';
}

// Obtenir l'icône appropriée pour un type de fichier
function getFileIcon(file) {
    const extension = file.name.split('.').pop().toLowerCase();
    
    const iconMap = {
        // Documents
        'pdf': 'far fa-file-pdf',
        'doc': 'far fa-file-word',
        'docx': 'far fa-file-word',
        'txt': 'far fa-file-alt',
        'rtf': 'far fa-file-alt',
        'odt': 'far fa-file-word',
        'xls': 'far fa-file-excel',
        'xlsx': 'far fa-file-excel',
        'csv': 'far fa-file-csv',
        'ppt': 'far fa-file-powerpoint',
        'pptx': 'far fa-file-powerpoint',
        // Archives
        'zip': 'far fa-file-archive',
        'rar': 'far fa-file-archive',
        '7z': 'far fa-file-archive',
        'tar': 'far fa-file-archive',
        'gz': 'far fa-file-archive',
        // Code
        'html': 'far fa-file-code',
        'css': 'far fa-file-code',
        'js': 'far fa-file-code',
        'json': 'far fa-file-code',
        'py': 'far fa-file-code',
        'java': 'far fa-file-code',
        'php': 'far fa-file-code',
        'sql': 'far fa-file-code',
        // Audio
        'mp3': 'far fa-file-audio',
        'wav': 'far fa-file-audio',
        'ogg': 'far fa-file-audio',
        // Vidéo
        'mp4': 'far fa-file-video',
        'mov': 'far fa-file-video',
        'avi': 'far fa-file-video',
        'mkv': 'far fa-file-video',
    };
    
    return iconMap[extension] || 'far fa-file';
}

// Formater la taille du fichier en format lisible
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Supprimer un fichier de la liste des fichiers à envoyer
function removeFile(fileName) {
    state.filesToUpload = state.filesToUpload.filter(file => file.name !== fileName);
    
    // Masquer le conteneur de prévisualisation s'il n'y a plus de fichiers
    if (state.filesToUpload.length === 0) {
        const previewContainer = document.getElementById('preview-attachments');
        if (previewContainer) {
            previewContainer.style.display = 'none';
        }
    }
}

// Réinitialiser la prévisualisation des fichiers
function resetFilePreview() {
    const previewContainer = document.getElementById('preview-attachments');
    if (previewContainer) {
        previewContainer.innerHTML = '';
        previewContainer.style.display = 'none';
    }
    
    state.filesToUpload = [];
    
    const fileInput = document.getElementById('file-upload');
    if (fileInput) {
        fileInput.value = '';
    }
}

// Configurer les gestionnaires d'événements pour les notifications
function setupNotificationHandlers() {
    // Marquer toutes les notifications comme lues
    const markAllReadBtn = document.getElementById('mark-all-read');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', () => {
            fetch(`${config.apiBaseUrl}/notifications/read-all/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to mark all notifications as read');
                }
                
                // Mettre à jour l'interface utilisateur
                document.querySelectorAll('.notification-item').forEach(item => {
                    item.classList.remove('unread');
                    const badge = item.querySelector('.notification-badge');
                    if (badge) {
                        badge.remove();
                    }
                });
                
                // Mettre à jour le compteur de notifications non lues
                updateUnreadCount('all');
                
                showToast('Succès', 'Toutes les notifications ont été marquées comme lues', 'success');
            })
            .catch(error => {
                console.error('Error marking all notifications as read:', error);
                showToast('Erreur', 'Impossible de marquer toutes les notifications comme lues', 'error');
            });
        });
    }
    
    // Supprimer une notification
    document.addEventListener('click', (e) => {
        if (e.target.closest('.notification-close')) {
            e.preventDefault();
            e.stopPropagation();
            
            const notificationItem = e.target.closest('.notification-item');
            if (!notificationItem) return;
            
            const notificationId = notificationItem.dataset.notificationId;
            if (!notificationId) return;
            
            fetch(`${config.apiBaseUrl}/notifications/${notificationId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to delete notification');
                }
                
                // Supprimer l'élément de notification du DOM
                notificationItem.remove();
                
                // Vérifier s'il reste des notifications
                const notificationsList = document.querySelector('.notifications-list');
                if (notificationsList && notificationsList.children.length === 0) {
                    notificationsList.innerHTML = `
                        <div class="empty-state">
                            <i class="far fa-bell-slash"></i>
                            <p>{% trans "Aucune notification" %}</p>
                            <small>{% trans "Lorsque vous recevrez des notifications, elles apparaîtront ici." %}</small>
                        </div>
                    `;
                }
                
                // Mettre à jour le compteur de notifications non lues
                updateUnreadCount(-1);
            })
            .catch(error => {
                console.error('Error deleting notification:', error);
                showToast('Erreur', 'Impossible de supprimer la notification', 'error');
            });
        }
    });
}

// Gérer une nouvelle notification
function handleNewNotification(notification) {
    // Mettre à jour le compteur de notifications non lues
    updateUnreadCount(1);
    
    // Afficher une notification toast si la fenêtre n'est pas active
    if (document.hidden) {
        showNotification(
            notification.sender_name || 'Nouvelle notification',
            notification.message,
            notification.sender_avatar
        );
    }
    
    // Mettre à jour la liste des notifications si elle est visible
    const notificationsList = document.querySelector('.notifications-list');
    if (notificationsList) {
        // Supprimer l'état vide s'il existe
        const emptyState = notificationsList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        // Créer le nouvel élément de notification
        const notificationElement = document.createElement('div');
        notificationElement.className = 'notification-item unread';
        notificationElement.dataset.notificationId = notification.id;
        notificationElement.dataset.notificationType = notification.type;
        
        if (notification.url) {
            notificationElement.dataset.url = notification.url;
            notificationElement.style.cursor = 'pointer';
            
            notificationElement.addEventListener('click', () => {
                window.location.href = notification.url;
            });
        }
        
        // Formater l'heure
        const notificationTime = new Date(notification.timestamp);
        const formattedTime = formatTimeAgo(notificationTime);
        
        // Construire le HTML de la notification
        let notificationHtml = `
            <div class="notification-avatar">
        `;
        
        if (notification.sender_avatar) {
            notificationHtml += `
                <img src="${notification.sender_avatar}" alt="${notification.sender_name}">
            `;
        } else {
            notificationHtml += `
                <div class="notification-icon">
                    <i class="${getNotificationIcon(notification.type)}"></i>
                </div>
            `;
        }
        
        notificationHtml += `
            </div>
            <div class="notification-content">
                <div class="notification-message">
                    ${notification.message}
                </div>
                <div class="notification-time">
                    ${formattedTime}
                </div>
            </div>
            <span class="notification-badge"></span>
            <button class="notification-close" data-notification-id="${notification.id}">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        notificationElement.innerHTML = notificationHtml;
        
        // Ajouter la notification en haut de la liste
        notificationsList.insertBefore(notificationElement, notificationsList.firstChild);
    }
}

// Obtenir l'icône appropriée pour le type de notification
function getNotificationIcon(notificationType) {
    const iconMap = {
        'message': 'fas fa-envelope',
        'mention': 'fas fa-at',
        'like': 'fas fa-heart',
        'comment': 'fas fa-comment',
        'follow': 'fas fa-user-plus',
        'system': 'fas fa-cog',
        'warning': 'fas fa-exclamation-triangle',
        'success': 'fas fa-check-circle',
        'error': 'fas fa-times-circle',
        'info': 'fas fa-info-circle',
    };
    
    return iconMap[notificationType] || 'fas fa-bell';
}

// Configurer les gestionnaires d'événements pour le mode mobile
function setupMobileHandlers() {
    // Bouton pour afficher/masquer la liste des conversations sur mobile
    const backToInboxBtn = document.getElementById('back-to-inbox');
    if (backToInboxBtn) {
        backToInboxBtn.addEventListener('click', () => {
            document.querySelector('.chat-sidebar').classList.add('active');
            document.querySelector('.chat-main').classList.remove('active');
        });
    }
    
    // Gestion du clic sur une conversation (mode mobile)
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.addEventListener('click', () => {
            if (window.innerWidth < 992) { // Breakpoint Bootstrap lg
                document.querySelector('.chat-sidebar').classList.remove('active');
                document.querySelector('.chat-main').classList.add('active');
            }
        });
    });
    
    // Gestion du redimensionnement de la fenêtre
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 992) {
            document.querySelector('.chat-sidebar').classList.remove('active');
            document.querySelector('.chat-main').classList.remove('active');
        }
    });
}

// Afficher une notification toast
function showToast(title, message, type = 'info') {
    // Créer l'élément toast
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.role = 'alert';
    
    // Construire le HTML du toast
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="${getToastIcon(type)}"></i>
        </div>
        <div class="toast-body">
            <h5 class="toast-title">${title}</h5>
            <p class="toast-message">${message}</p>
            <div class="toast-time">À l'instant</div>
        </div>
        <button type="button" class="toast-close" aria-label="Fermer">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Ajouter le toast au corps du document
    document.body.appendChild(toast);
    
    // Afficher le toast avec une animation
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // Configurer la fermeture automatique
    const dismissTimeout = setTimeout(() => {
        closeToast(toast);
    }, config.toastDuration);
    
    // Configurer le bouton de fermeture
    const closeButton = toast.querySelector('.toast-close');
    if (closeButton) {
        closeButton.addEventListener('click', () => {
            clearTimeout(dismissTimeout);
            closeToast(toast);
        });
    }
    
    // Fonction pour fermer le toast
    function closeToast(toastElement) {
        toastElement.classList.remove('show');
        setTimeout(() => {
            if (toastElement.parentNode) {
                toastElement.parentNode.removeChild(toastElement);
            }
        }, 300);
    }
}

// Obtenir l'icône appropriée pour le toast
function getToastIcon(type) {
    const iconMap = {
        'success': 'fas fa-check-circle',
        'error': 'fas fa-exclamation-circle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle',
    };
    
    return iconMap[type] || 'fas fa-bell';
}

// Afficher une notification système
function showNotification(title, message, icon = null) {
    // Vérifier si les notifications sont autorisées
    if (Notification.permission === 'granted') {
        const notification = new Notification(title, {
            body: message,
            icon: icon || '/static/images/logo.png',
        });
        
        // Rediriger vers l'application lors du clic sur la notification
        notification.onclick = function() {
            window.focus();
            this.close();
        };
        
        // Fermer la notification après 5 secondes
        setTimeout(() => {
            notification.close();
        }, 5000);
    } else if (Notification.permission !== 'denied') {
        // Demander l'autorisation si elle n'a pas encore été demandée
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                showNotification(title, message, icon);
            }
        });
    }
}

// Mettre à jour le statut d'un utilisateur
function updateUserStatus(data) {
    // Mettre à jour le statut dans la liste des conversations
    const conversationItems = document.querySelectorAll('.conversation-item');
    conversationItems.forEach(item => {
        if (parseInt(item.dataset.userId) === data.user_id) {
            const statusIndicator = item.querySelector('.user-status');
            if (statusIndicator) {
                statusIndicator.className = `user-status ${data.is_online ? 'online' : 'offline'}`;
                statusIndicator.title = data.is_online ? 'En ligne' : 'Hors ligne';
            }
        }
    });
    
    // Mettre à jour le statut dans l'en-tête de la conversation active
    if (state.currentRoomId && data.user_id === state.currentRoomId) {
        const statusElement = document.querySelector('.chat-header .online-status');
        if (statusElement) {
            statusElement.className = `online-status ${data.is_online ? 'online' : 'offline'}`;
            statusElement.nextSibling.textContent = data.is_online ? ' En ligne' : ' Hors ligne';
        }
    }
}

// Obtenir la valeur d'un cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Vérifier si le cookie commence par le nom suivi de '='
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
