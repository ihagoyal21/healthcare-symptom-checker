from flask import Flask, request, jsonify, render_template
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyDEUrkoFSLWShlNW99SmDLImiyzQa7k0LU" 
genai.configure(api_key=GEMINI_API_KEY)

# Define symptom to department mapping
symptom_to_department = {
    "Fever": "Internal Medicine",
    "Headache": "Neurology",
    "Cough": "Pulmonology",
    "Stomach Pain": "Gastroenterology",
    "Chest Pain": "Cardiology",
    "Rash": "Dermatology",
    "Joint Pain": "Orthopedics",
    "Sore Throat": "Otolaryngology",
    "Dizziness": "Neurology",
    "Fatigue": "Internal Medicine",
    "Other": "General Practice"
}

# Initialize conversation states
conversation_states = {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_id = data.get('user_id', 'default_user')
    message = data.get('message', '')
    is_option = data.get('is_option', False)
    
    print(f"Received message: '{message}', is_option: {is_option}, user_id: {user_id}")
    
    # Initialize conversation if new user
    if user_id not in conversation_states:
        print(f"Initializing new conversation for user {user_id}")
        conversation_states[user_id] = {
            "current_state": "name",
            "gathered_info": {},
            "current_step": 0
        }
    
    state = conversation_states[user_id]
    print(f"Current state: {state['current_state']}")
    
    # Process the message based on the current state
    if state["current_state"] == "name":
        # Store name and ask about symptoms
        if message != "Skip this step" and message != "Hello! I'm your healthcare assistant. Before we begin, could you tell me your name?":
            state["gathered_info"]["name"] = message
            greeting = f"Nice to meet you, {message}! "
        else:
            greeting = ""
        
        # Update state and prepare response for symptoms question
        state["current_state"] = "initial"
        response = f"{greeting}What symptoms are you experiencing today?"
        options = list(symptom_to_department.keys())
    
    elif state["current_state"] == "initial":
        # Case-insensitive symptom matching
        matched_symptom = None
        for symptom in symptom_to_department.keys():
            if symptom.lower() == message.lower():
                matched_symptom = symptom
                break
        
        if matched_symptom or is_option:
            # Use the matched symptom or the original message if is_option is True
            symptom_to_use = matched_symptom if matched_symptom else message
            state["gathered_info"]["main_symptom"] = symptom_to_use
            state["current_state"] = "duration"
            
            response = f"I see you're experiencing {symptom_to_use}. How long have you been experiencing this symptom?"
            options = ["Less than 24 hours", "1-3 days", "4-7 days", "More than a week"]
        else:
            # If user types something not in our options, try to match it
            response = "Please select one of the following symptoms that best matches your condition:"
            options = list(symptom_to_department.keys())
    
    elif state["current_state"] == "duration":
        # Store the duration
        state["gathered_info"]["duration"] = message
        state["current_state"] = "severity"
        
        response = "How would you rate the severity of your symptoms?"
        options = ["Mild", "Moderate", "Severe", "Very severe"]
    
    elif state["current_state"] == "severity":
        # Store the severity
        state["gathered_info"]["severity"] = message
        state["current_state"] = "additional"
        
        response = "Do you have any additional symptoms? (Select all that apply)"
        options = ["Fever", "Fatigue", "Nausea", "Dizziness", "Shortness of breath", "None of these"]
    
    elif state["current_state"] == "additional":
        # Store additional symptoms
        state["gathered_info"]["additional"] = message
        state["current_state"] = "medical_history"
        
        response = "Do you have any relevant medical history?"
        options = ["Diabetes", "Hypertension", "Heart disease", "Asthma", "None"]
    
    elif state["current_state"] == "medical_history":
        # Store medical history
        state["gathered_info"]["medical_history"] = message
        state["current_state"] = "recommendation"
        
        # Generate recommendation
        main_symptom = state["gathered_info"].get("main_symptom", "")
        department = symptom_to_department.get(main_symptom, "General Practice")
        
        print(f"Generating recommendation for symptom: {main_symptom}, department: {department}")
        
        # Use Gemini to generate a more detailed response
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Format the gathered info for a more personalized response
            name_prefix = ""
            if "name" in state["gathered_info"]:
                name_prefix = f"{state['gathered_info']['name']}, "
                
            prompt = f"""
            Based on the following patient information, provide a brief assessment and department recommendation:
            - Main symptom: {state['gathered_info'].get('main_symptom', 'Not specified')}
            - Duration: {state['gathered_info'].get('duration', 'Not specified')}
            - Severity: {state['gathered_info'].get('severity', 'Not specified')}
            - Additional symptoms: {state['gathered_info'].get('additional', 'None')}
            - Medical history: {state['gathered_info'].get('medical_history', 'None')}
            
            The recommended department is {department}.
            
            Provide a brief, empathetic response that:
            1. Addresses the patient as {name_prefix}if name is provided
            2. Acknowledges their symptoms
            3. Gives a brief assessment
            4. Recommends the appropriate department
            5. Asks if they would like to schedule an appointment
            6. Includes a brief medical disclaimer
            
            Keep the response concise and conversational.
            """
            
            response_obj = model.generate_content(prompt)
            detailed_response = response_obj.text
            
            # Update state for scheduling
            state["current_state"] = "scheduling"
            
            return jsonify({
                "response": detailed_response,
                "options": ["Yes, schedule appointment", "No, thank you"]
            })
            
        except Exception as e:
            print(f"Error generating response with Gemini: {str(e)}")
            # Fallback response if Gemini fails
            name_greeting = ""
            if "name" in state["gathered_info"]:
                name_greeting = f"{state['gathered_info']['name']}, "
                
            response = f"{name_greeting}based on your symptoms, I recommend consulting with our {department} department. Would you like to schedule an appointment?"
            options = ["Yes, schedule appointment", "No, thank you"]
            
            # Make sure to update the state
            state["current_state"] = "scheduling"
    
    elif state["current_state"] == "scheduling":
        if "yes" in message.lower() or "schedule" in message.lower():
            state["current_state"] = "appointment_time"
            response = "When would you like to schedule your appointment?"
            options = ["Tomorrow", "This week", "Next week", "As soon as possible"]
        else:
            state["current_state"] = "completed"
            response = "Thank you for using our symptom checker. If your symptoms worsen, please don't hesitate to seek medical attention. Is there anything else I can help you with?"
            options = ["Start over", "No, thank you"]
    
    elif state["current_state"] == "appointment_time":
        state["gathered_info"]["appointment_time"] = message
        state["current_state"] = "appointment_confirmed"
        
        # In a real app, this would connect to your scheduling system
        department = symptom_to_department.get(state["gathered_info"].get("main_symptom", ""), "General Practice")
        
        name_greeting = ""
        if "name" in state["gathered_info"]:
            name_greeting = f"{state['gathered_info']['name']}, "
            
        response = f"Great! {name_greeting}I've scheduled your appointment with the {department} department for {message}. You'll receive a confirmation shortly. Is there anything else I can help you with?"
        options = ["Start over", "No, thank you"]
    
    elif state["current_state"] == "completed" or state["current_state"] == "appointment_confirmed":
        if "start over" in message.lower():
            # Reset the conversation
            conversation_states[user_id] = {
                "current_state": "name",
                "gathered_info": {},
                "current_step": 0
            }
            response = "Hello! I'm your healthcare assistant. Before we begin, could you tell me your name?"
            options = ["Skip this step"]
        else:
            response = "Thank you for using our healthcare assistant. Have a great day!"
            options = ["Start over"]
    
    else:
        # Default fallback
        response = "I'm not sure how to proceed. Let's start over."
        state["current_state"] = "name"
        response = "Hello! I'm your healthcare assistant. Before we begin, could you tell me your name?"
        options = ["Skip this step"]
    
    print(f"Responding with: {response}")
    print(f"Options: {options}")
    print(f"New state: {state['current_state']}")
    
    return jsonify({
        "response": response,
        "options": options
    })

# Function to schedule an appointment (mock implementation)
@app.route('/schedule_appointment', methods=['POST'])
def schedule_appointment():
    data = request.json
    department = data.get('department')
    date = data.get('date')
    time = data.get('time')
    
    # In a real application, this would connect to your scheduling system
    # For now, return a mock response
    return jsonify({
        "status": "success",
        "appointment": {
            "department": department,
            "date": date,
            "time": time,
            "confirmation_code": "APT" + str(hash(f"{department}{date}{time}"))[:5]
        }
    })

if __name__ == '__main__':
    app.run(debug=True)
