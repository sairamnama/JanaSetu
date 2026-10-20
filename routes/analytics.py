"""
GramSeva - Civic Analytics Routes
Provides dashboard metrics, category breakdowns, ward performance, and department turnaround times.
"""

from flask import Blueprint, jsonify
from services.analytics_service import get_analytics_data

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api')

@analytics_bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Returns aggregated civic metrics and performance charts data."""
    data = get_analytics_data()
    return jsonify({
        'success': True,
        **data
    })
