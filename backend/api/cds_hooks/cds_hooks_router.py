"""
CDS Hooks Router
Implements CDS Hooks v1.0 specification with management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import json
import uuid
from enum import Enum
from database.database import get_db
from models.models import Patient, Encounter, Provider, Organization, Observation, Condition, Medication

router = APIRouter(tags=["CDS Hooks"])

# In-memory storage for hooks (in production, use database)
hooks_storage = {}

class IndicatorType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class CDSHookEngine:
    """CDS Hook execution engine"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def evaluate_hook(self, hook_config: dict, context: dict) -> List[dict]:
        """Evaluate a CDS hook against the given context"""
        cards = []
        
        # Check if conditions are met
        if self._evaluate_conditions(hook_config.get('conditions', []), context):
            # Execute actions
            for action in hook_config.get('actions', []):
                card = self._execute_action(action, context)
                if card:
                    cards.append(card)
        
        return cards
    
    def _evaluate_conditions(self, conditions: List[dict], context: dict) -> bool:
        """Evaluate all conditions (AND logic)"""
        if not conditions:
            return True  # No conditions means always trigger
        
        for condition in conditions:
            if not self._evaluate_condition(condition, context):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: dict, context: dict) -> bool:
        """Evaluate a single condition"""
        condition_type = condition.get('type')
        parameters = condition.get('parameters', {})
        patient_id = context.get('patientId')
        
        if not patient_id:
            return False
        
        # Get patient data
        patient = self.db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return False
        
        if condition_type == 'patient-age':
            return self._check_patient_age(patient, parameters)
        elif condition_type == 'patient-gender':
            return self._check_patient_gender(patient, parameters)
        elif condition_type == 'diagnosis-code':
            return self._check_diagnosis_code(patient_id, parameters)
        elif condition_type == 'medication-active':
            return self._check_active_medication(patient_id, parameters)
        elif condition_type == 'medication-missing':
            return not self._check_active_medication(patient_id, parameters)
        elif condition_type == 'lab-value':
            return self._check_lab_value(patient_id, parameters)
        elif condition_type == 'lab-missing':
            return self._check_lab_missing(patient_id, parameters)
        elif condition_type == 'vital-sign':
            return self._check_vital_sign(patient_id, parameters)
        
        return False
    
    def _check_patient_age(self, patient: Patient, parameters: dict) -> bool:
        """Check patient age condition"""
        if not patient.date_of_birth:
            return False
        
        age = (datetime.now().date() - patient.date_of_birth).days / 365.25
        operator = parameters.get('operator', 'eq')
        value = float(parameters.get('value', 0))
        
        if operator == 'eq':
            return abs(age - value) < 1  # Within 1 year
        elif operator == 'gt':
            return age > value
        elif operator == 'ge':
            return age >= value
        elif operator == 'lt':
            return age < value
        elif operator == 'le':
            return age <= value
        
        return False
    
    def _check_patient_gender(self, patient: Patient, parameters: dict) -> bool:
        """Check patient gender condition"""
        target_gender = parameters.get('value', '').lower()
        patient_gender = (patient.gender or '').lower()
        return patient_gender == target_gender
    
    def _check_diagnosis_code(self, patient_id: str, parameters: dict) -> bool:
        """Check for specific diagnosis codes"""
        codes = parameters.get('codes', '').split(',')
        codes = [code.strip() for code in codes if code.strip()]
        
        if not codes:
            return False
        
        # Check both SNOMED and ICD-10 codes (SNOMED is primary)
        conditions = self.db.query(Condition).filter(
            and_(
                Condition.patient_id == patient_id,
                Condition.clinical_status == 'active',
                or_(
                    Condition.snomed_code.in_(codes),
                    Condition.icd10_code.in_(codes) if Condition.icd10_code else False
                )
            )
        ).all()
        
        operator = parameters.get('operator', 'in')
        if operator == 'in':
            return len(conditions) > 0
        elif operator == 'not-in':
            return len(conditions) == 0
        
        return False
    
    def _check_active_medication(self, patient_id: str, parameters: dict) -> bool:
        """Check for active medications"""
        medications = parameters.get('medications', '').split(',')
        medications = [med.strip().lower() for med in medications if med.strip()]
        
        if not medications:
            return False
        
        active_meds = self.db.query(Medication).filter(
            and_(
                Medication.patient_id == patient_id,
                Medication.status == 'active'
            )
        ).all()
        
        for med in active_meds:
            med_name = med.medication_name.lower()
            for target_med in medications:
                if target_med in med_name:
                    return True
        
        return False
    
    def _check_lab_value(self, patient_id: str, parameters: dict) -> bool:
        """Check lab values against thresholds"""
        code = parameters.get('code')
        operator = parameters.get('operator', 'gt')
        value = float(parameters.get('value', 0))
        timeframe = int(parameters.get('timeframe', 30))  # days
        
        if not code:
            return False
        
        # Get recent lab results
        cutoff_date = datetime.now().date() - timedelta(days=timeframe)
        labs = self.db.query(Observation).filter(
            and_(
                Observation.patient_id == patient_id,
                Observation.observation_type == 'laboratory',
                Observation.loinc_code == code,
                Observation.observation_date >= cutoff_date
            )
        ).order_by(Observation.observation_date.desc()).all()
        
        if operator == 'missing':
            return len(labs) == 0
        
        if not labs:
            return False
        
        latest_lab = labs[0]
        try:
            # Try value_quantity first, then value
            if latest_lab.value_quantity is not None:
                lab_value = float(latest_lab.value_quantity)
            elif latest_lab.value:
                lab_value = float(latest_lab.value)
            else:
                return False
        except (ValueError, TypeError):
            return False
        
        if operator == 'gt':
            return lab_value > value
        elif operator == 'ge':
            return lab_value >= value
        elif operator == 'lt':
            return lab_value < value
        elif operator == 'le':
            return lab_value <= value
        elif operator == 'eq':
            return abs(lab_value - value) < 0.01
        
        return False
    
    def _check_lab_missing(self, patient_id: str, parameters: dict) -> bool:
        """Check if a lab test is missing within a timeframe"""
        code = parameters.get('code') or parameters.get('labTest')
        timeframe = int(parameters.get('timeframe', 90))  # days
        
        if not code:
            return False
        
        # Get recent lab results
        cutoff_date = datetime.now().date() - timedelta(days=timeframe)
        labs = self.db.query(Observation).filter(
            and_(
                Observation.patient_id == patient_id,
                Observation.observation_type == 'laboratory',
                Observation.loinc_code == code,
                Observation.observation_date >= cutoff_date
            )
        ).count()
        
        # Return True if no labs found (missing)
        return labs == 0
    
    def _check_vital_sign(self, patient_id: str, parameters: dict) -> bool:
        """Check vital signs against normal ranges"""
        vital_type = parameters.get('type')
        operator = parameters.get('operator', 'gt')
        value = float(parameters.get('value', 0))
        timeframe = int(parameters.get('timeframe', 7))  # days
        component = parameters.get('component', 'systolic')  # For blood pressure
        
        if not vital_type:
            return False
        
        # Get recent vital signs
        cutoff_date = datetime.now().date() - timedelta(days=timeframe)
        
        # Special handling for blood pressure
        if vital_type == '85354-9':  # Blood pressure panel LOINC code
            vitals = self.db.query(Observation).filter(
                and_(
                    Observation.patient_id == patient_id,
                    Observation.observation_type == 'vital-signs',
                    Observation.loinc_code == '85354-9',  # Blood pressure panel
                    Observation.observation_date >= cutoff_date
                )
            ).order_by(Observation.observation_date.desc()).all()
        else:
            # Use LOINC code for other vital signs
            vitals = self.db.query(Observation).filter(
                and_(
                    Observation.patient_id == patient_id,
                    Observation.observation_type == 'vital-signs',
                    Observation.loinc_code == vital_type,
                    Observation.observation_date >= cutoff_date
                )
            ).order_by(Observation.observation_date.desc()).all()
        
        if not vitals:
            return False
        
        latest_vital = vitals[0]
        try:
            # Handle blood pressure values (e.g., "126/76")
            if vital_type == '85354-9' and latest_vital.value:
                if '/' in latest_vital.value:
                    systolic, diastolic = latest_vital.value.split('/')
                    if component == 'systolic':
                        vital_value = float(systolic)
                    elif component == 'diastolic':
                        vital_value = float(diastolic)
                    else:
                        return False
                else:
                    return False
            # Try value_quantity first, then value
            elif latest_vital.value_quantity is not None:
                vital_value = float(latest_vital.value_quantity)
            elif latest_vital.value:
                vital_value = float(latest_vital.value)
            else:
                return False
        except (ValueError, TypeError):
            return False
        
        if operator == 'gt':
            return vital_value > value
        elif operator == 'ge':
            return vital_value >= value
        elif operator == 'lt':
            return vital_value < value
        elif operator == 'le':
            return vital_value <= value
        
        return False
    
    def _execute_action(self, action: dict, context: dict) -> Optional[dict]:
        """Execute an action and return a CDS card"""
        action_type = action.get('type')
        parameters = action.get('parameters', {})
        
        if action_type in ['info-card', 'warning-card', 'critical-card']:
            return self._create_card(action_type, parameters, context)
        elif action_type == 'suggestion':
            return self._create_suggestion(parameters, context)
        elif action_type == 'link':
            return self._create_link(parameters, context)
        
        return None
    
    def _create_card(self, card_type: str, parameters: dict, context: dict) -> dict:
        """Create a CDS card"""
        indicator_map = {
            'info-card': 'info',
            'warning-card': 'warning',
            'critical-card': 'critical'
        }
        
        return {
            "summary": parameters.get('summary', 'Clinical Alert'),
            "detail": parameters.get('detail', ''),
            "indicator": indicator_map.get(card_type, 'info'),
            "source": {
                "label": parameters.get('source', 'Clinical Decision Support'),
                "url": parameters.get('sourceUrl', ''),
                "icon": parameters.get('sourceIcon', '')
            },
            "uuid": str(uuid.uuid4())
        }
    
    def _create_suggestion(self, parameters: dict, context: dict) -> dict:
        """Create a suggestion card"""
        return {
            "summary": parameters.get('label', 'Clinical Suggestion'),
            "detail": parameters.get('description', ''),
            "indicator": "info",
            "suggestions": [
                {
                    "label": parameters.get('label', 'Suggestion'),
                    "uuid": str(uuid.uuid4()),
                    "actions": [
                        {
                            "type": parameters.get('type', 'create'),
                            "description": parameters.get('description', ''),
                            "resource": parameters.get('resource', {})
                        }
                    ]
                }
            ],
            "uuid": str(uuid.uuid4())
        }
    
    def _create_link(self, parameters: dict, context: dict) -> dict:
        """Create a link card"""
        return {
            "summary": parameters.get('label', 'External Resource'),
            "detail": f"Link to: {parameters.get('url', '')}",
            "indicator": "info",
            "links": [
                {
                    "label": parameters.get('label', 'Open Link'),
                    "url": parameters.get('url', ''),
                    "type": parameters.get('type', 'absolute'),
                    "appContext": parameters.get('appContext', '')
                }
            ],
            "uuid": str(uuid.uuid4())
        }

# CDS Hooks Discovery Endpoint
@router.get("/")
async def discover_hooks():
    """CDS Hooks discovery endpoint"""
    return {
        "services": [
            {
                "hook": hook_config.get("hook"),
                "title": hook_config.get("title"),
                "description": hook_config.get("description"),
                "id": hook_id,
                "prefetch": hook_config.get("prefetch", {}),
                "usageRequirements": hook_config.get("usageRequirements", "")
            }
            for hook_id, hook_config in hooks_storage.items()
            if hook_config.get("enabled", True)
        ]
    }

# Hook Management Endpoints (must come before the generic /{hook_id} route)
@router.get("/hooks")
async def list_hooks():
    """List all CDS hooks"""
    return list(hooks_storage.values())

@router.post("/hooks")
async def create_hook(hook_config: dict):
    """Create a new CDS hook"""
    hook_id = hook_config.get("id")
    if not hook_id:
        raise HTTPException(status_code=400, detail="Hook ID is required")
    
    if hook_id in hooks_storage:
        raise HTTPException(status_code=409, detail="Hook ID already exists")
    
    # Add metadata
    hook_config.update({
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })
    
    hooks_storage[hook_id] = hook_config
    return hook_config

# CDS Hook Execution Endpoints (generic route must come after specific routes)
@router.post("/{hook_id}")
async def execute_hook(
    hook_id: str,
    request: dict,
    db: Session = Depends(get_db)
):
    """Execute a specific CDS hook"""
    hook_config = hooks_storage.get(hook_id)
    if not hook_config:
        raise HTTPException(status_code=404, detail="Hook not found")
    
    if not hook_config.get("enabled", True):
        return {"cards": []}
    
    # Create execution engine
    engine = CDSHookEngine(db)
    
    # Convert request to context
    context = {
        "hookInstance": request.get("hookInstance"),
        "fhirServer": request.get("fhirServer"),
        "hook": request.get("hook"),
        "patientId": request.get("context", {}).get("patientId"),
        "userId": request.get("context", {}).get("userId"),
        "encounterId": request.get("context", {}).get("encounterId"),
        **request.get("context", {})
    }
    
    # Execute hook
    cards = engine.evaluate_hook(hook_config, context)
    
    return {"cards": cards}

@router.get("/hooks/{hook_id}")
async def get_hook(hook_id: str):
    """Get a specific CDS hook"""
    hook_config = hooks_storage.get(hook_id)
    if not hook_config:
        raise HTTPException(status_code=404, detail="Hook not found")
    return hook_config

@router.put("/hooks/{hook_id}")
async def update_hook(hook_id: str, hook_config: dict):
    """Update a CDS hook"""
    if hook_id not in hooks_storage:
        raise HTTPException(status_code=404, detail="Hook not found")
    
    # Preserve creation date, update modification date
    hook_config.update({
        "created_at": hooks_storage[hook_id].get("created_at"),
        "updated_at": datetime.now().isoformat()
    })
    
    hooks_storage[hook_id] = hook_config
    return hook_config

@router.delete("/hooks/{hook_id}")
async def delete_hook(hook_id: str):
    """Delete a CDS hook"""
    if hook_id not in hooks_storage:
        raise HTTPException(status_code=404, detail="Hook not found")
    
    del hooks_storage[hook_id]
    return {"message": "Hook deleted successfully"}

@router.post("/hooks/{hook_id}/test")
async def test_hook(
    hook_id: str,
    test_context: dict,
    db: Session = Depends(get_db)
):
    """Test a CDS hook with sample data"""
    hook_config = hooks_storage.get(hook_id)
    if not hook_config:
        raise HTTPException(status_code=404, detail="Hook not found")
    
    # Create execution engine
    engine = CDSHookEngine(db)
    
    # Execute hook with test context
    cards = engine.evaluate_hook(hook_config, test_context)
    
    return {
        "hookId": hook_id,
        "testContext": test_context,
        "result": {"cards": cards},
        "timestamp": datetime.now().isoformat()
    }

# Initialize with some sample hooks
def initialize_sample_hooks():
    """Initialize with sample CDS hooks for demonstration - updated for Synthea data"""
    sample_hooks = {
        "diabetes-a1c-monitoring": {
            "id": "diabetes-a1c-monitoring",
            "title": "Diabetes A1C Monitoring",
            "description": "Monitors A1C values and testing frequency for diabetic patients",
            "hook": "patient-view",
            "priority": 1,
            "enabled": True,
            "conditions": [
                {
                    "id": "1",
                    "type": "lab-value",
                    "parameters": {
                        "code": "4548-4",  # Hemoglobin A1c
                        "operator": "gt",
                        "value": "7.0",
                        "timeframe": "180"
                    }
                }
            ],
            "actions": [
                {
                    "id": "1",
                    "type": "warning-card",
                    "parameters": {
                        "summary": "Elevated A1C",
                        "detail": "Patient's A1C is above target (>7%). Consider intensifying diabetes management.",
                        "indicator": "warning",
                        "source": "ADA Standards of Care"
                    }
                }
            ],
            "fhirVersion": "4.0.1"
        },
        "kidney-function-alert": {
            "id": "kidney-function-alert",
            "title": "Kidney Function Alert",
            "description": "Monitors kidney function based on eGFR and creatinine",
            "hook": "patient-view",
            "priority": 1,
            "enabled": True,
            "conditions": [
                {
                    "id": "1",
                    "type": "lab-value",
                    "parameters": {
                        "code": "33914-3",  # eGFR
                        "operator": "lt",
                        "value": "60",
                        "timeframe": "90"
                    }
                }
            ],
            "actions": [
                {
                    "id": "1",
                    "type": "warning-card",
                    "parameters": {
                        "summary": "Reduced Kidney Function",
                        "detail": "Patient's eGFR is <60 mL/min/1.73m². Consider nephrology referral and medication adjustments.",
                        "indicator": "warning",
                        "source": "KDIGO Guidelines"
                    }
                }
            ],
            "fhirVersion": "4.0.1"
        },
        "glucose-management": {
            "id": "glucose-management",
            "title": "Glucose Management Alert",
            "description": "Alerts for abnormal glucose values",
            "hook": "patient-view",
            "priority": 1,
            "enabled": True,
            "conditions": [
                {
                    "id": "1",
                    "type": "lab-value",
                    "parameters": {
                        "code": "2339-0",  # Glucose
                        "operator": "gt",
                        "value": "180",
                        "timeframe": "7"
                    }
                }
            ],
            "actions": [
                {
                    "id": "1",
                    "type": "critical-card",
                    "parameters": {
                        "summary": "Hyperglycemia Alert",
                        "detail": "Recent glucose >180 mg/dL. Evaluate diabetes management and consider medication adjustment.",
                        "indicator": "critical",
                        "source": "Clinical Alert"
                    }
                }
            ],
            "fhirVersion": "4.0.1"
        },
        "pain-assessment-followup": {
            "id": "pain-assessment-followup",
            "title": "Pain Management Follow-up",
            "description": "Reminds providers to follow up on high pain scores",
            "hook": "patient-view",
            "priority": 2,
            "enabled": True,
            "conditions": [
                {
                    "id": "1",
                    "type": "lab-value",
                    "parameters": {
                        "code": "72514-3",  # Pain severity score
                        "operator": "ge",
                        "value": "7",
                        "timeframe": "7"
                    }
                }
            ],
            "actions": [
                {
                    "id": "1",
                    "type": "warning-card",
                    "parameters": {
                        "summary": "High Pain Score",
                        "detail": "Patient reported severe pain (≥7/10) recently. Consider pain management review and interventions.",
                        "indicator": "warning",
                        "source": "Pain Management Guidelines"
                    }
                }
            ],
            "fhirVersion": "4.0.1"
        },
        "elderly-comprehensive-care": {
            "id": "elderly-comprehensive-care",
            "title": "Elderly Comprehensive Care",
            "description": "Comprehensive care reminders for elderly patients",
            "hook": "patient-view",
            "priority": 3,
            "enabled": True,
            "conditions": [
                {
                    "id": "1",
                    "type": "patient-age",
                    "parameters": {
                        "operator": "ge",
                        "value": "65"
                    }
                }
            ],
            "actions": [
                {
                    "id": "1",
                    "type": "info-card",
                    "parameters": {
                        "summary": "Geriatric Care Considerations",
                        "detail": "Consider:\n- Fall risk assessment\n- Medication review (polypharmacy)\n- Cognitive screening\n- Social needs assessment (PRAPARE)\n- Advance care planning",
                        "indicator": "info",
                        "source": "Geriatric Care Guidelines"
                    }
                }
            ],
            "fhirVersion": "4.0.1"
        },
        "blood-pressure-monitoring": {
            "id": "blood-pressure-monitoring",
            "title": "Blood Pressure Monitoring",
            "description": "Monitors blood pressure values and alerts for hypertension",
            "hook": "patient-view",
            "priority": 1,
            "enabled": True,
            "conditions": [
                {
                    "id": "1",
                    "type": "vital-sign",
                    "parameters": {
                        "type": "85354-9",
                        "component": "systolic",
                        "operator": "ge",
                        "value": "140",
                        "timeframe": "3650"
                    }
                }
            ],
            "actions": [
                {
                    "id": "1",
                    "type": "warning-card",
                    "parameters": {
                        "summary": "Stage 2 Hypertension",
                        "detail": "Patient's systolic blood pressure is ≥140 mmHg. Consider antihypertensive therapy per ACC/AHA guidelines.",
                        "indicator": "warning",
                        "source": "ACC/AHA Hypertension Guidelines",
                        "sourceUrl": "https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings"
                    }
                }
            ],
            "fhirVersion": "4.0.1"
        },
        "stage-1-hypertension": {
            "id": "stage-1-hypertension",
            "title": "Stage 1 Hypertension Alert",
            "description": "Alerts for Stage 1 Hypertension (systolic 130-139 or diastolic 80-89)",
            "hook": "patient-view",
            "priority": 2,
            "enabled": True,
            "conditions": [
                {
                    "id": "1",
                    "type": "vital-sign",
                    "parameters": {
                        "type": "85354-9",
                        "component": "systolic",
                        "operator": "ge",
                        "value": "130",
                        "timeframe": "90"
                    }
                }
            ],
            "actions": [
                {
                    "id": "1",
                    "type": "info-card",
                    "parameters": {
                        "summary": "Stage 1 Hypertension",
                        "detail": "Patient's blood pressure indicates Stage 1 Hypertension (≥130/80). Consider lifestyle modifications and cardiovascular risk assessment.",
                        "indicator": "info",
                        "source": "ACC/AHA Hypertension Guidelines"
                    }
                }
            ],
            "fhirVersion": "4.0.1"
        },
        "hypertensive-crisis": {
            "id": "hypertensive-crisis",
            "title": "Hypertensive Crisis Alert",
            "description": "Alerts for hypertensive crisis (systolic ≥180 or diastolic ≥120)",
            "hook": "patient-view",
            "priority": 1,
            "enabled": True,
            "conditions": [
                {
                    "id": "1",
                    "type": "vital-sign",
                    "parameters": {
                        "type": "85354-9",
                        "component": "systolic",
                        "operator": "ge",
                        "value": "180",
                        "timeframe": "1"
                    }
                }
            ],
            "actions": [
                {
                    "id": "1",
                    "type": "critical-card",
                    "parameters": {
                        "summary": "Hypertensive Crisis",
                        "detail": "Patient's systolic blood pressure is ≥180 mmHg. Immediate evaluation and treatment needed.",
                        "indicator": "critical",
                        "source": "ACC/AHA Hypertension Guidelines",
                        "sourceUrl": "https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings/hypertensive-crisis-when-you-should-call-911-for-high-blood-pressure"
                    }
                }
            ],
            "fhirVersion": "4.0.1"
        },
        "opioid-risk-assessment": {
            "id": "opioid-risk-assessment",
            "title": "Opioid Risk Assessment",
            "description": "Alerts for patients on opioid medications",
            "hook": "medication-prescribe",
            "priority": 1,
            "enabled": True,
            "conditions": [
                {
                    "id": "1",
                    "type": "medication-active",
                    "parameters": {
                        "medications": "oxycodone,hydrocodone,fentanyl",
                        "operator": "in"
                    }
                }
            ],
            "actions": [
                {
                    "id": "1",
                    "type": "warning-card",
                    "parameters": {
                        "summary": "Opioid Safety Alert",
                        "detail": "Patient is on opioid therapy. Consider:\n- Risk assessment (ORT/SOAPP)\n- Naloxone prescription\n- State PDMP check\n- Urine drug screening",
                        "indicator": "warning",
                        "source": "CDC Opioid Guidelines"
                    }
                }
            ],
            "fhirVersion": "4.0.1"
        },
        "missing-diabetes-labs": {
            "id": "missing-diabetes-labs",
            "title": "Missing Diabetes Labs",
            "description": "Alerts when diabetic patients are missing routine labs",
            "hook": "patient-view",
            "priority": 2,
            "enabled": True,
            "conditions": [
                {
                    "id": "1",
                    "type": "diagnosis-code",
                    "parameters": {
                        "codes": "44054006",
                        "operator": "in"
                    }
                },
                {
                    "id": "2",
                    "type": "lab-missing",
                    "parameters": {
                        "labTest": "4548-4",
                        "timeframe": "90"
                    },
                    "logic": "AND"
                }
            ],
            "actions": [
                {
                    "id": "1",
                    "type": "info-card",
                    "parameters": {
                        "summary": "A1C Due for Diabetes Patient",
                        "detail": "Patient with diabetes has not had an A1C test in over 90 days. ADA recommends quarterly monitoring for most patients with diabetes.",
                        "indicator": "info",
                        "source": "ADA Standards of Care"
                    }
                }
            ],
            "fhirVersion": "4.0.1"
        },
        "statin-for-diabetes": {
            "id": "statin-for-diabetes",
            "title": "Statin Therapy for Diabetes",
            "description": "Recommends statin therapy for diabetic patients not on statins",
            "hook": "patient-view",
            "priority": 3,
            "enabled": True,
            "conditions": [
                {
                    "id": "1",
                    "type": "diagnosis-code",
                    "parameters": {
                        "codes": "44054006",
                        "operator": "in"
                    }
                },
                {
                    "id": "2",
                    "type": "patient-age",
                    "parameters": {
                        "operator": "ge",
                        "value": "40"
                    },
                    "logic": "AND"
                },
                {
                    "id": "3",
                    "type": "medication-missing",
                    "parameters": {
                        "medications": "atorvastatin,simvastatin,rosuvastatin,pravastatin"
                    },
                    "logic": "AND"
                }
            ],
            "actions": [
                {
                    "id": "1",
                    "type": "suggestion",
                    "parameters": {
                        "label": "Consider Statin Therapy",
                        "description": "Patient with diabetes age ≥40 not on statin therapy. ADA recommends moderate-intensity statin therapy for primary prevention.",
                        "source": "ADA Standards of Care"
                    }
                }
            ],
            "fhirVersion": "4.0.1"
        }
    }
    
    hooks_storage.update(sample_hooks)

# Initialize sample hooks on startup
initialize_sample_hooks()