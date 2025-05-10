from fhirclient import client
from fhirclient.models.patient import Patient
from fhirclient.models.humanname import HumanName
from fhirclient.models.contactpoint import ContactPoint
from fhirclient.models.fhirdate import FHIRDate
from fhirclient.models.fhirinstant import FHIRInstant
from fhirclient.models.appointment import Appointment, AppointmentParticipant
from fhirclient.models.fhirreference import FHIRReference
from fhirclient.models.codeableconcept import CodeableConcept
from fhirclient.models.coding import Coding
from fhirclient.models.extension import Extension
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FHIRConnector:
    """A class to handle FHIR API interactions"""
    
    def __init__(self, api_base="http://localhost:8080/fhir", app_id="fhir_client"):
        """
        Initialize the FHIR client
        
        Args:
            api_base (str): The base URL of the FHIR server
            app_id (str): Application identifier
        """
        self.settings = {'app_id': app_id, 'api_base': api_base}
        self.client = client.FHIRClient(settings=self.settings)
        logger.info(f"FHIR client initialized with base URL: {api_base}")
    
    def create_patient(self, data):
        """
        Create a patient record in the FHIR server
        
        Args:
            data (dict): Patient information
            
        Returns:
            str: The ID of the created patient resource
        """
        try:
            patient = Patient()
            
            # Add name
            name = HumanName()
            name.given = [data.get("first_name", "")]
            if data.get("middle_name"):
                name.given.append(data.get("middle_name"))
            name.family = data.get("last_name", "")
            if data.get("prefix"):
                name.prefix = [data.get("prefix")]
            if data.get("suffix"):
                name.suffix = [data.get("suffix")]
            patient.name = [name]
            
            # Add contact information
            telecoms = []
            
            if "email" in data:
                email = ContactPoint()
                email.system = "email"
                email.value = data["email"]
                email.use = "home"  # Could be work, mobile, etc.
                telecoms.append(email)
            
            if "phone" in data:
                phone = ContactPoint()
                phone.system = "phone"
                phone.value = data["phone"]
                phone.use = "mobile"  # Could be home, work, etc.
                telecoms.append(phone)
                
            if telecoms:
                patient.telecom = telecoms
            
            # Add date of birth
            if "dob" in data:
                patient.birthDate = FHIRDate(data["dob"])
            
            # Add gender if available
            if "gender" in data:
                patient.gender = data["gender"]  # 'male', 'female', 'other', 'unknown'
            
            # Add any specific identifiers if provided
            if "identifiers" in data:
                patient.identifier = data["identifiers"]
            
            # Create the patient on the FHIR server
            created = patient.create(self.client.server)
            patient_id = created['id']
            logger.info(f"Patient created successfully with ID: {patient_id}")
            return patient_id
            
        except Exception as e:
            logger.error(f"Error creating patient: {str(e)}")
            raise
    
    def create_appointment(self, data):
        """
        Create an appointment in the FHIR server
        
        Args:
            data (dict): Appointment information
            
        Returns:
            dict: The created appointment resource
        """
        try:
            appointment = Appointment()
            appointment.status = "booked"  # could be: proposed, pending, booked, arrived, fulfilled, cancelled, etc.
            
            # Set appointment times
            appointment.start = FHIRInstant(data["start"])
            appointment.end = FHIRInstant(data["end"])
            
            # Set appointment type if provided
            if "type" in data:
                appointment_type = CodeableConcept()
                coding = Coding()
                coding.code = data["type"].get("code", "")
                coding.display = data["type"].get("display", "")
                coding.system = data["type"].get("system", "http://terminology.hl7.org/CodeSystem/v2-0276")
                appointment_type.coding = [coding]
                appointment.appointmentType = appointment_type
            
            # Add participants
            participants = []
            
            # Add patient as participant
            if "patient_id" in data:
                participant = AppointmentParticipant()
                participant_reference = FHIRReference()
                participant_reference.reference = f"Patient/{data['patient_id']}"
                participant.actor = participant_reference
                participant.status = "accepted"
                participant.required = "required"
                participants.append(participant)
            
            # Set participants
            appointment.participant = participants
            
            # Add description if provided
            if "description" in data:
                appointment.description = data["description"]
            
            # Add reason code if provided
            if "reason_code" in data:
                reason = CodeableConcept()
                reason_coding = Coding()
                reason_coding.code = data["reason_code"].get("code", "")
                reason_coding.display = data["reason_code"].get("display", "")
                reason_coding.system = data["reason_code"].get("system", "http://terminology.hl7.org/CodeSystem/appointment-reason")
                reason.coding = [reason_coding]
                appointment.reasonCode = [reason]
            
            # Create the appointment on the FHIR server
            created = appointment.create(self.client.server)
            logger.info(f"Appointment created successfully with ID: {created['id']}")
            return created  # Return the dictionary directly
            
        except Exception as e:
            logger.error(f"Error creating appointment: {str(e)}")
            raise
    
    def get_patient(self, patient_id):
        """
        Retrieve a patient by ID
        
        Args:
            patient_id (str): The ID of the patient to retrieve
            
        Returns:
            Patient: The retrieved patient resource
        """
        try:
            patient = Patient.read(patient_id, self.client.server)
            return patient
        except Exception as e:
            logger.error(f"Error retrieving patient {patient_id}: {str(e)}")
            raise
    
    def get_appointment(self, appointment_id):
        """
        Retrieve an appointment by ID
        
        Args:
            appointment_id (str): The ID of the appointment to retrieve
            
        Returns:
            Appointment: The retrieved appointment resource
        """
        try:
            appointment = Appointment.read(appointment_id, self.client.server)
            return appointment
        except Exception as e:
            logger.error(f"Error retrieving appointment {appointment_id}: {str(e)}")
            raise

# Example usage
if __name__ == "__main__":
    # Initialize the FHIR connector
    fhir = FHIRConnector()
    
    # Example patient data
    patient_data = {
        "first_name": "John",
        "middle_name": "Alfred",
        "last_name": "Smith",
        "prefix": "Mr.",
        "email": "john.smith@example.com",
        "phone": "555-123-4567",
        "gender": "male",
        "dob": "1980-07-15"
    }
    
    # Create the patient
    patient_id = fhir.create_patient(patient_data)
    
    # Example appointment data
    appointment_data = {
        "patient_id": patient_id,
        "start": "2025-05-15T10:00:00Z",
        "end": "2025-05-15T10:30:00Z",
        "description": "Annual physical examination",
        "type": {
            "code": "CHECKUP",
            "display": "Routine check-up",
            "system": "http://terminology.hl7.org/CodeSystem/v2-0276"
        },
        "reason_code": {
            "code": "ANNUALPHYS",
            "display": "Annual physical",
            "system": "http://terminology.hl7.org/CodeSystem/appointment-reason"
        }
    }
    
    # Create the appointment
    appointment = fhir.create_appointment(appointment_data)
    print(f"Created appointment: {json.dumps(appointment, indent=2)}")