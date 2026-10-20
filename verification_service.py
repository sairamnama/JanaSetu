"""
GramSeva Verification Service Compatibility Layer
Maintains backwards compatibility for existing modules importing from verification_service.py.
Forwards to modular components in services.verification_service.
"""

from services.verification_service import (
    VerificationAttemptResult,
    VerificationService,
    MockVerificationService,
    BaseVerificationService,
    MockTelephonyVerificationService,
    ProductionTelephonyVerificationService,
    ProductionTwilioOrExotelService,
    get_verification_service,
    CALL_OUTCOMES,
    CITIZEN_RESPONSES,
    VERIFICATION_METHODS
)
