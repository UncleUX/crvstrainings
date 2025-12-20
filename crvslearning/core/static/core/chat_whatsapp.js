let currentRecipient = '';
let chatInput = $('#input');
let messageList = $('#messages');
let socket = null;

let userList = []; // latest_message,username

// this will be used to store the date of the last message
// in the message area
let lastDate = "";

// Function to initialize WebSocket connection
function initWebSocket() {
    let wsStart = 'ws://';
    if (window.location.protocol == 'https:') {
        wsStart = 'wss://';
    }
    
    const wsUrl = wsStart + window.location.host + '/ws/ws/';
    console.log('Connecting to WebSocket:', wsUrl);
    
    socket = new WebSocket(wsUrl);
    
    socket.onopen = function(e) {
        console.log('WebSocket connection established');
        // Afficher un message de connexion réussie
        const connectionMessage = {
            id: 'connection_' + Date.now(),
            type: 'system',
            message: 'Connected to chat server',
            timestamp: new Date().toISOString()
        };
        console.log('Connection message:', connectionMessage);
    };
    
    socket.onmessage = function(e) {
        console.log('Raw WebSocket message received:', e.data);
        try {
            const data = JSON.parse(e.data);
            console.log('Parsed WebSocket data:', data);
            
            if (data.type === 'chat_message' && data.message) {
                // Traiter le message de chat
                const message = data.message;
                console.log('Processing chat message:', message);
                
                // Vérifier si le message est pour la conversation actuelle
                if ((message.user === currentRecipient || message.recipient === currentRecipient) || 
                    (message.recipient === currentUser && message.user === currentRecipient)) {
                    
                    // Vérifier si le message n'existe pas déjà
                    if (!$(`#message-${message.id}`).length) {
                        console.log('Drawing new message:', message);
                        drawMessage(message);
                        messageList.animate({scrollTop: messageList.prop('scrollHeight')});
                    }
                }
                
                // Mettre à jour la liste des utilisateurs dans tous les cas
                updateUserList(message);
                
            } else if (data.type === 'connection_established') {
                console.log('WebSocket connection confirmed:', data);
            } else {
                console.log('Unhandled WebSocket message type:', data.type);
            }
        } catch (error) {
            console.error('Error processing WebSocket message:', error, 'Raw data:', e.data);
        }
    };
    
    socket.onclose = function(event) {
        console.log('WebSocket connection closed:', event);
        // Afficher un message de déconnexion
        const disconnectMessage = {
            id: 'disconnect_' + Date.now(),
            type: 'system',
            message: 'Disconnected from chat server. Reconnecting...',
            timestamp: new Date().toISOString()
        };
        console.log('Disconnect message:', disconnectMessage);
        
        // Essayer de se reconnecter après 5 secondes
        setTimeout(initWebSocket, 5000);
    };
    
    socket.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
}

function fetchUserList() {
    $.getJSON('/api/v1/user/', function (data) {
        userList = data;
        drawUserList();
    });
}

function drawUserList() {
    $('#user-list').empty();
    // sort users based on latest message timestamp
    userList.sort((a,b)=>new Date(b.timestamp) - new Date(a.timestamp));
    for (let i = 0; i < userList.length; i++) {
        const msg = userList[i]['latest_message'];
        const userItem = `
            <div class="chat-list-item d-flex flex-row w-100 p-2 border-bottom${currentRecipient === userList[i]['username'] ? " active" : ""}" 
                onclick="onClickUserList(this, '${userList[i]['username']}')">
                <img src="${static_url}/img/profilepic.png" alt="Profile Photo" class="img-fluid rounded-circle mr-2" style="height:50px;">
                <div class="w-50">
                    <div class="name">${userList[i]['username']}</div>
                    <div class="small last-message">${msg ? msg.substr(0, 50) : ""}</div>
                </div>
                <div class="flex-grow-1 text-right">
                    <div class="small time">${showDateUserlist(userList[i]['timestamp'])}</div>
                </div>
            </div>`;
        $(userItem).appendTo('#user-list');
    }
}


function getTime(dateString){
  if (!dateString) return ''
  let date = new Date(dateString);
  let dualize = (x) => x < 10 ? "0" + x : x;
  return dualize(date.getHours()) + ":" + dualize(date.getMinutes());
}

function showDateUserlist(dateString) {
    let weekdaydate = showDatesWeekDays(dateString);
    if (weekdaydate === 'TODAY') 
        return getTime(dateString)
    return weekdaydate
}

function showDatesWeekDays(dateString) {
    if (!dateString) return ''
    const dt = new Date(dateString)        
    let days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']; 

    let date_weekday = dt.toLocaleDateString();
    if (dt.toDateString() == new Date().toDateString()) {
        date_weekday = 'TODAY';
    } else if(dt > new Date(Date.now() - 604800000)) {
        // if date is greater than last 7 days date
        date_weekday = days[dt.getDay()].toUpperCase()
    }
    return date_weekday;
}

function drawMessage(message) {
    let msgDate = showDatesWeekDays(message.timestamp);
    let messageItem = '';
    if (lastDate != msgDate) {
        messageItem += `<div class="mx-auto my-2 bg-info text-white small py-1 px-2 rounded">
            ${msgDate}
        </div>`;
        lastDate = msgDate;
    }
    messageItem += `
    <div class="align-self-${message.user === currentUser ? "end self" : "start"} p-1 my-1 mx-3 rounded bg-white shadow-sm message-item">
        <div class="options">
            <a href="#"><i class="fas fa-angle-down text-muted px-2"></i></a>
        </div>
        <div class="d-flex flex-row">
            <div class="body m-1 mr-2">${message.body}</div>
            <div class="time ml-auto small text-right flex-shrink-0 align-self-end text-muted" style="width:75px;">
                ${getTime(message.timestamp)}
            </div>
        </div>
    </div>`;
    // alert(messageItem)
    $(messageItem).appendTo('#messages');
}

function onClickUserList(elem,recipient) {
    currentRecipient = recipient;
    $("#name").text(recipient);
    $.getJSON(`/api/v1/message/?target=${recipient}`, function (data) {
        messageList.empty(); // .children('.message-item').remove();
        $(".overlay").addClass("d-none");
        $("#input-area").removeClass("d-none").addClass("d-flex");

        $(".chat-list-item").removeClass("active");
        $(elem).addClass("active");
        lastDate = "";
        for (let i = data['results'].length - 1; i >= 0; i--) {
            drawMessage(data['results'][i]);
        }
        messageList.animate({scrollTop: messageList.prop('scrollHeight')});
    });
}

function updateUserList(data) {
    // add latest message to userlist
    // id, user, recipient, timestamp, body
    let data_username = data.user;
    if (data.user === currentUser) {
        data_username = data.recipient;
    }

    const obj = userList.find(v => v.username === data_username); obj.latest_message = data.body; obj.timestamp = data.timestamp;
    
    drawUserList();
}
function getMessageById(message) {
    try {
        // Vérifier si le message est déjà un objet ou une chaîne JSON
        const messageData = typeof message === 'string' ? JSON.parse(message) : message;
        
        // Si c'est un message WebSocket, extraire les données du message
        const messageObj = messageData.message ? 
            (typeof messageData.message === 'string' ? JSON.parse(messageData.message) : messageData.message) : 
            messageData;
            
        console.log('Processing message:', messageObj);
        
        // Vérifier si le message est pour la conversation actuelle
        if (messageObj.user === currentRecipient || 
            (messageObj.recipient === currentRecipient && messageObj.user === currentUser)) {
            
            // Vérifier si le message n'existe pas déjà
            if (!$(`#message-${messageObj.id}`).length) {
                drawMessage(messageObj);
                messageList.animate({scrollTop: messageList.prop('scrollHeight')});
            }
        }
        
        // Mettre à jour la liste des utilisateurs dans tous les cas
        updateUserList(messageObj);
        
    } catch (error) {
        console.error('Error processing message:', error, 'Original message:', message);
    }
}


function sendMessage() {
    const body = chatInput.val().trim();
    if (body.length > 0 && currentRecipient) {
        console.log('Sending message to', currentRecipient, ':', body);
        
        // Trouver l'ID du destinataire
        const recipientData = userList.find(user => user.username === currentRecipient);
        if (!recipientData) {
            console.error('Recipient not found in user list');
            return;
        }
        
        // Envoyer le message via WebSocket
        if (socket && socket.readyState === WebSocket.OPEN) {
            const messageData = {
                type: 'chat_message',
                recipient_id: recipientData.id,
                message: body
            };
            
            socket.send(JSON.stringify(messageData));
            chatInput.val('');
        } else {
            console.error('WebSocket is not connected');
            // Fallback vers AJAX si WebSocket n'est pas disponible
            $.ajax({
                url: '/api/v1/message/',
                type: 'POST',
                data: {
                    recipient: currentRecipient,
                    body: body
                },
                success: function(response) {
                    console.log('Message sent via AJAX:', response);
                    chatInput.val('');
                    // Recharger les messages
                    if (currentRecipient) {
                        $.getJSON(`/api/v1/message/?target=${currentRecipient}`, function (data) {
                            messageList.empty();
                            data.results.forEach(drawMessage);
                            messageList.animate({scrollTop: messageList.prop('scrollHeight')});
                        });
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error sending message:', error);
                    alert('Error sending message. Please check console for details.');
                }
            });
        }
    } else if (!currentRecipient) {
        alert('Veuillez d\'abord sélectionner un destinataire');
    }
}


let showProfileSettings = () => {
    $("#profile-settings").css("left", 0); //.style.left = 0;
    // DOM.profilePic.src = user.pic;
    // DOM.inputName.value = user.name;
};

let hideProfileSettings = () => {
    $("#profile-settings").css("left", "-110%");
    // DOM.username.innerHTML = user.name;
};

$(document).ready(function () {
    // Initialize WebSocket connection
    initWebSocket();
    
    // Load user list
    fetchUserList();
    
    // Handle enter key press
    chatInput.keypress(function (e) {
        if (e.keyCode == 13) sendMessage();
    });
    
    // Show input area when a user is selected
    $(document).on('click', '.chat-list-item', function() {
        $('#input-area').removeClass('d-none');
    });
});
