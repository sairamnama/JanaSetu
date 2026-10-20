"""
GramSeva Verification Service Abstraction
Provides phone/IVR citizen verification interfaces for Rural Panchayats.
Includes an extensible abstraction for real telephony providers (Twilio, Exotel, etc.)
and a clearly identified Mock implementation for development and testing.
"""

from abc import ABC, abstractmethod
from datetime import datetime
import os
import re
import uuid
from core.constants import CALL_OUTCOMES, CITIZEN_RESPONSES, VERIFICATION_METHODS
from core.security import mask_phone


class VerificationAttemptResult:
    """
    Represents the structured result of a citizen resolution verification attempt.
    Stores complete verification request metadata:
    - grievance ID
    - citizen ID
    - phone number reference (masked)
    - attempt number
    - requested time
    - call outcome
    - citizen response
    - response time
    - provider reference
    - status
    """
    def __init__(
        self,
        call_outcome: str,
        citizen_response: str = None,
        grievance_id: int = None,
        citizen_id: int = None,
        phone_number_ref: str = None,
        attempt_number: int = 1,
        requested_time: str = None,
        response_time: str = None,
        provider_ref: str = None,
        provider_call_id: str = None,
        status: str = None,
        remarks: str = ""
    ):
        if call_outcome not in CALL_OUTCOMES:
            raise ValueError(f"Invalid call outcome '{call_outcome}'. Allowed: {CALL_OUTCOMES}")
        if citizen_response is not None and citizen_response not in CITIZEN_RESPONSES:
            raise ValueError(f"Invalid citizen response '{citizen_response}'. Allowed: {CITIZEN_RESPONSES}")

        # Invariant: NO_ANSWER (or any non-answered outcome) must NEVER be interpreted as NO or any response
        if call_outcome != 'ANSWERED' and citizen_response is not None:
            citizen_response = None

        self.call_outcome = call_outcome
        self.citizen_response = citizen_response
        self.grievance_id = grievance_id
        self.citizen_id = citizen_id
        self.phone_number_ref = phone_number_ref
        self.attempt_number = attempt_number
        
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.requested_time = requested_time or now_ts
        self.response_time = response_time or now_ts

        resolved_prov = provider_ref or provider_call_id or f"MOCK-CALL-{uuid.uuid4().hex[:8].upper()}"
        self.provider_ref = resolved_prov
        self.provider_call_id = resolved_prov

        if status:
            self.status = status
        else:
            if call_outcome == 'ANSWERED':
                self.status = 'COMPLETED'
            elif call_outcome in ('NO_ANSWER', 'BUSY'):
                self.status = 'PENDING_RETRY'
            else:
                self.status = 'FAILED'

        self.remarks = remarks
        self.timestamp = self.response_time

    @property
    def phone_ref(self):
        return self.phone_number_ref

    def to_dict(self):
        return {
            'grievance_id': self.grievance_id,
            'citizen_id': self.citizen_id,
            'phone_number_ref': self.phone_number_ref,
            'phone_ref': self.phone_number_ref,
            'attempt_number': self.attempt_number,
            'requested_time': self.requested_time,
            'call_outcome': self.call_outcome,
            'citizen_response': self.citizen_response,
            'response_time': self.response_time,
            'provider_ref': self.provider_ref,
            'provider_call_id': self.provider_ref,
            'status': self.status,
            'remarks': self.remarks,
            'timestamp': self.timestamp
        }


class VerificationService(ABC):
    """
    Abstract interface for citizen verification.
    Decouples the grievance verification workflow from external telephony carriers.
    Subclasses integrate with telephony/IVR providers (Twilio, Exotel, etc.)
    or provide development simulation mocks.
    """

    @abstractmethod
    def trigger_citizen_verification_call(
        self,
        grievance_id: int,
        contact_number: str,
        citizen_id: int = None,
        prompt_details: dict = None,
        **kwargs
    ) -> VerificationAttemptResult:
        """
        Triggers an outbound phone/IVR call to the citizen to verify resolution.
        Returns a VerificationAttemptResult with call outcome and response.
        """
        pass

    @abstractmethod
    def validate_citizen_response(self, response: str) -> bool:
        """Validates if the citizen response is one of YES, PARTIALLY, NO, UNABLE_TO_VERIFY."""
        pass

    def mask_phone_number(self, phone: str) -> str:
        """Helper to mask phone numbers according to privacy rules."""
        return mask_phone(phone)


# Backwards compatibility alias
BaseVerificationService = VerificationService


class MockVerificationService(VerificationService):
    """
    ===========================================================================
    DEVELOPMENT / MOCK VERIFICATION SERVICE
    Clearly labeled: Development / Mock Verification
    ===========================================================================
    Simulates automated phone / IVR calls to rural citizens for local development.
    Does NOT require a paid external provider or claim a real phone call occurred.
    Simulates:
        Call initiated
              ↓
        Call answered / Outcome
              ↓
        Citizen response
    """

    PROVIDER_LABEL = "Development / Mock Verification"

    def __init__(self):
        self.service_name = "MockVerificationService-v2.0"
        self.provider_label = self.PROVIDER_LABEL

    def validate_citizen_response(self, response: str) -> bool:
        return response in CITIZEN_RESPONSES

    def trigger_citizen_verification_call(
        self,
        grievance_id: int,
        contact_number: str,
        citizen_id: int = None,
        prompt_details: dict = None,
        **kwargs
    ) -> VerificationAttemptResult:
        """
        Simulates an automated IVR verification call in Development / Mock mode.
        Accepts optional 'simulated_outcome', 'simulated_response', 'attempt_number',
        'requested_time', and 'remarks' in kwargs for test suite & admin simulation UI.
        """
        simulated_outcome = kwargs.get('simulated_outcome')
        simulated_response = kwargs.get('simulated_response')
        attempt_number = kwargs.get('attempt_number', 1)
        requested_time = kwargs.get('requested_time')
        remarks = kwargs.get('remarks', '')

        # Generate masked phone reference to avoid exposing citizen PII
        phone_number_ref = self.mask_phone_number(contact_number)
        provider_ref = kwargs.get('provider_ref') or f"MOCK-IVR-{uuid.uuid4().hex[:8].upper()}"

        # Clean number to check format validity
        cleaned_number = re.sub(r'\D', '', str(contact_number))
        if len(cleaned_number) < 10:
            return VerificationAttemptResult(
                call_outcome='INVALID_NUMBER',
                citizen_response=None,
                grievance_id=grievance_id,
                citizen_id=citizen_id,
                phone_number_ref=phone_number_ref,
                attempt_number=attempt_number,
                requested_time=requested_time,
                provider_ref=provider_ref,
                status='FAILED',
                remarks=f"[{self.PROVIDER_LABEL}] Invalid phone number format '{phone_number_ref}'. Call could not be placed."
            )

        if simulated_outcome:
            outcome = simulated_outcome
            # Invariant: NO_ANSWER or non-answered call outcome NEVER yields a citizen response
            resp = simulated_response if outcome == 'ANSWERED' else None

            if outcome == 'ANSWERED':
                sim_msg = f"[{self.PROVIDER_LABEL}] Simulated call initiated -> Call answered -> Citizen response: {resp or 'UNABLE_TO_VERIFY'}."
            elif outcome == 'NO_ANSWER':
                sim_msg = f"[{self.PROVIDER_LABEL}] Simulated call initiated -> Ringing timed out (NO_ANSWER). Issue remains pending verification."
            elif outcome == 'BUSY':
                sim_msg = f"[{self.PROVIDER_LABEL}] Simulated call initiated -> Line busy / rejected (BUSY). Issue remains pending verification."
            elif outcome == 'INVALID_NUMBER':
                sim_msg = f"[{self.PROVIDER_LABEL}] Simulated call initiated -> Carrier unreachable (INVALID_NUMBER)."
            else:
                sim_msg = f"[{self.PROVIDER_LABEL}] Simulated call initiated -> Network connection failed (FAILED)."

            full_remarks = f"{sim_msg} {remarks}".strip()

            return VerificationAttemptResult(
                call_outcome=outcome,
                citizen_response=resp,
                grievance_id=grievance_id,
                citizen_id=citizen_id,
                phone_number_ref=phone_number_ref,
                attempt_number=attempt_number,
                requested_time=requested_time,
                provider_ref=provider_ref,
                remarks=full_remarks
            )

        # Default fallback simulation if no explicit override provided
        return VerificationAttemptResult(
            call_outcome='ANSWERED',
            citizen_response='YES',
            grievance_id=grievance_id,
            citizen_id=citizen_id,
            phone_number_ref=phone_number_ref,
            attempt_number=attempt_number,
            requested_time=requested_time,
            provider_ref=provider_ref,
            remarks=f"[{self.PROVIDER_LABEL}] Simulated call initiated -> Call answered -> Citizen confirmed issue resolution (YES)."
        )


# Backwards compatibility alias
MockTelephonyVerificationService = MockVerificationService


class ProductionTelephonyVerificationService(VerificationService):
    """
    Production Telephony Service Connector (Twilio / Exotel / Sarv / Asterisk).
    Pluggable provider that replaces MockVerificationService in production without
    modifying any grievance workflow or lifecycle state-machine code.
    Requires environment credentials:
    - TELEPHONY_PROVIDER = 'twilio' or 'exotel'
    - TELEPHONY_ACCOUNT_SID
    - TELEPHONY_AUTH_TOKEN
    - TELEPHONY_CALLER_ID
    """

    def __init__(self):
        self.provider_name = os.environ.get('TELEPHONY_PROVIDER', 'twilio').lower()
        self.account_sid = os.environ.get('TELEPHONY_ACCOUNT_SID')
        self.auth_token = os.environ.get('TELEPHONY_AUTH_TOKEN')
        self.caller_id = os.environ.get('TELEPHONY_CALLER_ID')

    def validate_citizen_response(self, response: str) -> bool:
        return response in CITIZEN_RESPONSES

    def trigger_citizen_verification_call(
        self,
        grievance_id: int,
        contact_number: str,
        citizen_id: int = None,
        prompt_details: dict = None,
        **kwargs
    ) -> VerificationAttemptResult:
        if not self.account_sid or not self.auth_token:
            raise NotImplementedError(
                f"Production telephony provider '{self.provider_name}' is not configured. "
                "Set TELEPHONY_ACCOUNT_SID and TELEPHONY_AUTH_TOKEN in environment variables, "
                "or use MockVerificationService for local development."
            )
        # Production REST API dispatch logic goes here
        raise NotImplementedError("Production provider client integration pending live telephony credentials.")


# Backwards compatibility alias
ProductionTwilioOrExotelService = ProductionTelephonyVerificationService


def get_verification_service() -> VerificationService:
    """
    Factory method to return the active verification service instance.
    Decouples callers from knowing whether mock or real telephony is active.
    """
    provider = os.environ.get('TELEPHONY_PROVIDER', 'mock').lower()
    if provider in ('twilio', 'exotel'):
        return ProductionTelephonyVerificationService()
    return MockVerificationService()
