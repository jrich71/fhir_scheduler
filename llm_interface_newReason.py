import gradio as gr
import openai
import google.generativeai as genai
import os
from dotenv import load_dotenv
from fhir_utils import FHIRConnector
import re
import json
from datetime import datetime

# Load environment variables
load_dotenv()
#openai.api_key = os.getenv("OPENAI_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize your FHIR interface
fhir = FHIRConnector()

# ChatGPT: Define LLM helper
# def ask_llm(prompt):
#     response = openai.OpenAI().chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {"role": "system", "content": "You are a helpful assistant for creating FHIR-compliant medical appointments."},
#             {"role": "user", "content": prompt}
#         ]
#     )
#     return response["choices"][0]["message"]["content"]

# Gemini: Define LLM helper
def ask_llm(prompt):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash")
    chat = model.start_chat()

    try:
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        print("❌ Gemini API error:", e)
        return None

# Strip any Markdown code fences from LLM output
def clean_json(text):
    if text is None:
        return ""
    return re.sub(r"```(?:json)?|```", "", text).strip()

# Define main function
def create_appointment_ui(name, dob, gender, reason):
    try:
        # Split full name into first and last
        first_name, *last_name_parts = name.strip().split(" ")
        last_name = " ".join(last_name_parts) if last_name_parts else "Unknown"

        # Normalize gender
        gender = gender.lower()
        if gender not in ["male", "female", "other", "unknown"]:
            gender = "unknown"

        # Format DOB
        try:
            dob = datetime.strptime(dob, "%Y-%m-%d").date().isoformat()
        except ValueError:
            dob = "1900-01-01"

        # Prompt Gemini for structured FHIR metadata
        gemini_prompt = (
            f"The patient described the reason for their visit as: '{reason}'. "
            "Return a JSON object with the following fields only:\n"
            "- refined_reason: a concise, FHIR-ready appointment description\n"
            "- appointment_type_code: a code from http://terminology.hl7.org/CodeSystem/v2-0276 "
            "(e.g., CHECKUP, FOLLOWUP, EMERGENCY, ROUTINE, etc.)\n"
            "- appointment_type_display: label for that code\n"
            "- reason_code: SNOMED or FHIR appointment reason code\n"
            "- reason_display: label for that reason\n"
            "Respond with JSON only. Do not include code blocks or natural language."
        )

        gemini_response = ask_llm(gemini_prompt)

        if not gemini_response:
            return "❌ Gemini returned no content."

        try:
            result = json.loads(clean_json(gemini_response))
        except json.JSONDecodeError as e:
            return f"❌ JSON parsing failed. Gemini said:\n{gemini_response}\n\nError: {str(e)}"

        # Extract LLM values
        refined_reason = result.get("refined_reason", reason)
        type_code = result.get("appointment_type_code", "CHECKUP")
        type_display = result.get("appointment_type_display", "Routine check-up")
        reason_code = result.get("reason_code", "UNSPECIFIED")
        reason_display = result.get("reason_display", refined_reason)

        # Create Patient
        patient_data = {
            "first_name": first_name,
            "last_name": last_name,
            "dob": dob,
            "gender": gender
        }

        patient_id = fhir.create_patient(patient_data)

        # Create Appointment
        appointment_data = {
            "patient_id": patient_id,
            "start": "2025-06-01T09:00:00Z",
            "end": "2025-06-01T09:30:00Z",
            "description": refined_reason,
            "type": {
                "code": type_code,
                "display": type_display,
                "system": "http://terminology.hl7.org/CodeSystem/v2-0276"
            },
            # Point to a SNOMED FHIR API?
            "reason_code": {
                "code": reason_code,
                "display": reason_display,
                "system": "http://terminology.hl7.org/CodeSystem/appointment-reason"
            }
        }

        appointment = fhir.create_appointment(appointment_data)

        return (
            f"✅ Appointment created for:\n"
            f"Name: {name}\n"
            f"Reason: {refined_reason}\n"
            f"Appointment Type: {type_display}\n"
            #f"Reason Code: {reason_code} - {reason_display}\n"
            f"Appointment ID: {appointment.get('id')}" # References the unique logical identifier for the patient resource
        )

    except Exception as e:
        return f"❌ Error: {str(e)}"

# Gradio UI
gr.Interface(
    fn=create_appointment_ui,
    inputs=[
        gr.Text(label="Patient Full Name"),
        gr.Text(label="Date of Birth (YYYY-MM-DD)"),
        gr.Text(label="Gender"),
        gr.Text(label="Reason for Visit")
    ],
    outputs=gr.Text(label="Result"),
    title="FHIR Appointment Scheduler",
    description="Enter patient information to generate and submit a FHIR Appointment using Gemini for language refinement."
).launch(server_port=8081)
