

class VoiceExpenseRecorder {
    constructor() {
        this.recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        this.recognition.continuous = false;
        this.recognition.lang = 'en-US';
        this.setupRecognition();
    }

    setupRecognition() {
        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            this.parseExpense(transcript);
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            alert('Error recording voice. Please try again.');
        };
    }

    parseExpense(transcript) {
        // Simple regex to extract amount and description
        const amountRegex = /\$?\d+(\.\d{2})?/;
        const amount = transcript.match(amountRegex);
        
        if (amount) {
            const amountValue = amount[0].replace('$', '');
            const description = transcript.replace(amount[0], '').trim();
            
            // Fill in the form
            document.getElementById('description').value = description;
            document.getElementById('amount').value = amountValue;
        } else {
            alert('Could not detect amount in the voice input. Please try again.');
        }
    }

    startRecording() {
        this.recognition.start();
    }

    stopRecording() {
        this.recognition.stop();
    }
}

// Initialize voice recorder when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const voiceRecorder = new VoiceExpenseRecorder();
    
    const voiceButton = document.getElementById('voice-record');
    if (voiceButton) {
        let isRecording = false;
        
        voiceButton.addEventListener('click', () => {
            if (!isRecording) {
                voiceRecorder.startRecording();
                voiceButton.textContent = 'Stop Recording';
                voiceButton.classList.remove('bg-blue-500', 'hover:bg-blue-600');
                voiceButton.classList.add('bg-red-500', 'hover:bg-red-600');
            } else {
                voiceRecorder.stopRecording();
                voiceButton.textContent = 'Record Expense';
                voiceButton.classList.remove('bg-red-500', 'hover:bg-red-600');
                voiceButton.classList.add('bg-blue-500', 'hover:bg-blue-600');
            }
            isRecording = !isRecording;
        });
    }
});
