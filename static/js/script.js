// Generate a random user ID for this session
const userId = 'user_' + Math.random().toString(36).substring(2, 15);
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const voiceButton = document.getElementById('voiceButton');

// Initialize by setting up the initial options
document.addEventListener('DOMContentLoaded', function() {
    // Set up click handlers for the initial option buttons
    const initialOptions = document.querySelectorAll('#initialOptions .option-button');
    initialOptions.forEach(button => {
        button.addEventListener('click', function() {
            handleOptionSelection(this.textContent);
        });
    });
});

// Function to add a message to the chat
function addMessage(message, isUser) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');
    messageDiv.textContent = message;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Function to display option buttons
function displayOptions(options) {
    // Create container for options
    const optionsContainer = document.createElement('div');
    optionsContainer.classList.add('options-container');
    
    // Create a button for each option
    options.forEach(option => {
        const button = document.createElement('button');
        button.classList.add('option-button');
        button.textContent = option;
        button.addEventListener('click', function() {
            handleOptionSelection(option);
        });
        optionsContainer.appendChild(button);
    });
    
    // Add options to chat
    chatMessages.appendChild(optionsContainer);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Hide any existing option containers (except the one we just added)
    const previousOptions = document.querySelectorAll('.options-container:not(:last-child)');
    previousOptions.forEach(container => {
        container.style.display = 'none';
    });
}

// Function to handle when an option button is clicked
async function handleOptionSelection(selectedOption) {
    // Display the selected option as a user message
    addMessage(selectedOption, true);
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                message: selectedOption,
                is_option: true
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            addMessage('Sorry, there was an error processing your request: ' + data.error, false);
        } else {
            // Display the bot's response
            addMessage(data.response, false);
            
            // If there are options to display, show them
            if (data.options && data.options.length > 0) {
                displayOptions(data.options);
            }
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('Sorry, there was an error connecting to the server.', false);
    }
}

// Function to send a text message to the server
async function sendMessage() {
    const message = userInput.value.trim();
    if (message === '') return;
    
    addMessage(message, true);
    userInput.value = '';
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                message: message,
                is_option: false
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            addMessage('Sorry, there was an error processing your request: ' + data.error, false);
        } else {
            addMessage(data.response, false);
            
            // If there are options to display, show them
            if (data.options && data.options.length > 0) {
                displayOptions(data.options);
            }
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('Sorry, there was an error connecting to the server.', false);
    }
}

// Function to schedule an appointment
async function scheduleAppointment(department, date, time) {
    try {
        const response = await fetch('/schedule_appointment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                department: department,
                date: date,
                time: time
            })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error scheduling appointment:', error);
        return { error: 'Failed to schedule appointment' };
    }
}

// Set up voice recognition
function setupSpeechRecognition() {
    if ('webkitSpeechRecognition' in window) {
        const recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
        };
        
        voiceButton.addEventListener('click', function() {
            recognition.start();
            voiceButton.textContent = '🔴';
        });
        
        recognition.onend = function() {
            voiceButton.textContent = '🎤';
        };
    } else {
        voiceButton.style.display = 'none';
    }
}

// Event listeners
sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// Initialize speech recognition
setupSpeechRecognition();
