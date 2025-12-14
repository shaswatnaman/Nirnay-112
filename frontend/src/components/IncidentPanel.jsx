/**
 * IncidentPanel component for displaying incident information.
 * 
 * This component shows real-time incident data including:
 * - Name of the reporter
 * - Location of the incident
 * - Type of incident
 * - Urgency level (color-coded)
 * - Human intervention requirement
 * 
 * Updates automatically from WebSocket incident summary messages.
 */

import React from 'react';
import './IncidentPanel.css';

const IncidentPanel = ({ incident = null }) => {
  /**
   * Get urgency color for visual indication.
   * 
   * @param {string} urgency - Urgency level (critical, high, medium, low)
   * @returns {string} CSS class name for urgency color
   */
  const getUrgencyColor = (urgency) => {
    if (!urgency) return 'urgency-medium';
    
    switch (urgency.toLowerCase()) {
      case 'critical':
        return 'urgency-critical';
      case 'high':
        return 'urgency-high';
      case 'medium':
        return 'urgency-medium';
      case 'low':
        return 'urgency-low';
      default:
        return 'urgency-medium';
    }
  };

  /**
   * Get urgency label for display.
   * 
   * @param {string} urgency - Urgency level
   * @returns {string} Formatted urgency label
   */
  const getUrgencyLabel = (urgency) => {
    if (!urgency) return 'Medium';
    
    const labels = {
      'critical': 'Critical',
      'high': 'High',
      'medium': 'Medium',
      'low': 'Low'
    };
    
    return labels[urgency.toLowerCase()] || 'Medium';
  };

  /**
   * Get incident type label.
   * 
   * @param {string} type - Incident type
   * @returns {string} Formatted type label
   */
  const getIncidentTypeLabel = (type) => {
    if (!type) return 'Not specified';
    
    const labels = {
      'accident': 'Accident',
      'crime': 'Crime',
      'medical': 'Medical',
      'fire': 'Fire',
      'other': 'Other'
    };
    
    return labels[type.toLowerCase()] || type;
  };

  /**
   * Format confidence as percentage.
   * 
   * @param {number} confidence - Confidence score (0.0-1.0)
   * @returns {string} Formatted percentage
   */
  const formatConfidence = (confidence) => {
    if (confidence === null || confidence === undefined) return 'N/A';
    return `${(confidence * 100).toFixed(0)}%`;
  };

  // Extract incident data
  const incidentData = incident?.incident || incident || {};
  const confidence = incident?.confidence || {};
  const missingFields = incident?.missing_fields || [];
  const humanRequired = incident?.human_required || false;

  return (
    <div className="incident-panel">
      <div className="panel-header">
        <h2>Incident Information</h2>
        {humanRequired && (
          <div className="human-required-badge">
            <span className="badge-icon">⚠️</span>
            <span>Human Required</span>
          </div>
        )}
      </div>

      <div className="incident-content">
        {/* Name Field */}
        <div className="incident-field">
          <div className="field-label">
            <span className="label-icon">👤</span>
            <span>Name</span>
          </div>
          <div className="field-value">
            {incidentData.name || (
              <span className="field-empty">
                {missingFields.includes('name') ? 'Missing' : 'Not provided'}
              </span>
            )}
          </div>
          {confidence.name !== undefined && (
            <div className="field-confidence">
              Confidence: {formatConfidence(confidence.name)}
            </div>
          )}
        </div>

        {/* Location Field */}
        <div className="incident-field">
          <div className="field-label">
            <span className="label-icon">📍</span>
            <span>Location</span>
          </div>
          <div className="field-value">
            {incidentData.location || (
              <span className="field-empty field-critical">
                {missingFields.includes('location') ? 'Missing (Critical)' : 'Not provided'}
              </span>
            )}
          </div>
          {confidence.location !== undefined && (
            <div className="field-confidence">
              Confidence: {formatConfidence(confidence.location)}
            </div>
          )}
        </div>

        {/* Incident Type Field */}
        <div className="incident-field">
          <div className="field-label">
            <span className="label-icon">🚨</span>
            <span>Incident Type</span>
          </div>
          <div className="field-value">
            {incidentData.incident_type ? (
              <span className="incident-type-badge">
                {getIncidentTypeLabel(incidentData.incident_type)}
              </span>
            ) : (
              <span className="field-empty field-critical">
                {missingFields.includes('incident_type') ? 'Missing (Critical)' : 'Not specified'}
              </span>
            )}
          </div>
          {confidence.incident_type !== undefined && (
            <div className="field-confidence">
              Confidence: {formatConfidence(confidence.incident_type)}
            </div>
          )}
        </div>

        {/* Urgency Field */}
        <div className="incident-field">
          <div className="field-label">
            <span className="label-icon">⚡</span>
            <span>Urgency</span>
          </div>
          <div className="field-value">
            {incidentData.urgency ? (
              <span className={`urgency-badge ${getUrgencyColor(incidentData.urgency)}`}>
                {getUrgencyLabel(incidentData.urgency)}
              </span>
            ) : (
              <span className="field-empty">
                {missingFields.includes('urgency') ? 'Missing' : 'Not specified'}
              </span>
            )}
          </div>
          {confidence.urgency !== undefined && (
            <div className="field-confidence">
              Confidence: {formatConfidence(confidence.urgency)}
            </div>
          )}
        </div>

        {/* Overall Confidence */}
        {incident?.completeness !== undefined && (
          <div className="incident-field completeness-field">
            <div className="field-label">
              <span className="label-icon">📊</span>
              <span>Completeness</span>
            </div>
            <div className="field-value">
              <div className="completeness-bar">
                <div 
                  className="completeness-fill"
                  style={{ width: `${(incident.completeness * 100)}%` }}
                />
                <span className="completeness-text">
                  {formatConfidence(incident.completeness)}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Missing Fields Indicator */}
        {missingFields.length > 0 && (
          <div className="missing-fields">
            <div className="missing-fields-header">
              <span className="label-icon">⚠️</span>
              <span>Missing Fields</span>
            </div>
            <div className="missing-fields-list">
              {missingFields.map((field, index) => (
                <span key={index} className="missing-field-tag">
                  {field}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default IncidentPanel;

