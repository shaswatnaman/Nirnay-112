/**
 * IncidentDetailsPanel component for displaying structured incident information.
 * 
 * Shows real-time incident data with confidence scores and timestamps.
 * Updates automatically from WebSocket incident summary messages.
 */

import React from 'react';
import './IncidentPanel.css';

const IncidentPanel = ({ incident = null }) => {
  /**
   * Get incident type label.
   */
  const getIncidentTypeLabel = (type) => {
    if (!type) return 'Unknown';
    
    const labels = {
      'accident': 'Accident',
      'crime': 'Crime',
      'medical': 'Medical',
      'fire': 'Fire',
      'natural_disaster': 'Natural Disaster',
      'other': 'Other'
    };
    
    return labels[type.toLowerCase()] || type;
  };

  /**
   * Format confidence as percentage.
   */
  const formatConfidence = (confidence) => {
    if (confidence === null || confidence === undefined) return 'N/A';
    return `${(confidence * 100).toFixed(0)}%`;
  };

  /**
   * Format timestamp for display.
   */
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return null;
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
    } catch (error) {
      return null;
    }
  };

  // Extract incident data
  const incidentData = incident?.incident || incident || {};
  const confidence = incident?.confidence || {};
  const missingFields = incident?.missing_fields || [];
  const humanRequired = incident?.human_required || false;

  return (
    <div className="incident-panel">
      <div className="panel-header">
        <h2>Incident Details</h2>
        {humanRequired && (
          <div className="human-required-badge">
            <span>HUMAN REQUIRED</span>
          </div>
        )}
      </div>

      <div className="incident-content">
        {/* Caller Name Field */}
        <div className="incident-field">
          <div className="field-label">Caller Name</div>
          <div className="field-value">
            {incidentData.name ? (
              <span>{incidentData.name}</span>
            ) : (
              <span className="field-empty">
                {missingFields.includes('name') ? 'Missing' : 'Awaiting confirmation'}
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
          <div className="field-label">Location</div>
          <div className="field-value">
            {incidentData.location ? (
              <span>{incidentData.location}</span>
            ) : (
              <span className="field-empty field-critical">
                {missingFields.includes('location') ? 'Missing (Critical)' : 'Awaiting confirmation'}
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
          <div className="field-label">Incident Type</div>
          <div className="field-value">
            {incidentData.incident_type ? (
              <span className="incident-type-badge">
                {getIncidentTypeLabel(incidentData.incident_type)}
              </span>
            ) : (
              <span className="field-empty field-critical">
                {missingFields.includes('incident_type') ? 'Missing (Critical)' : 'Unknown'}
              </span>
            )}
          </div>
          {confidence.incident_type !== undefined && (
            <div className="field-confidence">
              Confidence: {formatConfidence(confidence.incident_type)}
            </div>
          )}
        </div>

        {/* People Affected Field */}
        <div className="incident-field">
          <div className="field-label">People Affected</div>
          <div className="field-value">
            {incidentData.people_affected !== null && incidentData.people_affected !== undefined ? (
              <span>{incidentData.people_affected}</span>
            ) : (
              <span className="field-empty">Not provided</span>
            )}
          </div>
          {confidence.people_affected !== undefined && (
            <div className="field-confidence">
              Confidence: {formatConfidence(confidence.people_affected)}
            </div>
          )}
        </div>

        {/* Immediate Danger Field */}
        {incidentData.immediate_danger && (
          <div className="incident-field">
            <div className="field-label">Immediate Danger</div>
            <div className="field-value">
              <span className="danger-badge">ACTIVE</span>
            </div>
          </div>
        )}

        {/* System Signals (Layer 3 - For dispatcher view) */}
        {incident?.ml_signals && (
          <div className="incident-field system-signals">
            <div className="field-label">System Signals</div>
            <div className="field-value">
              <div className="system-signals-grid">
                <div className="system-signal-item">
                  <span className="system-signal-label">Clarity:</span>
                  <span className="system-signal-value">{formatConfidence(incident.ml_signals.clarity_avg || 0)}</span>
                </div>
                <div className="system-signal-item">
                  <span className="system-signal-label">Language:</span>
                  <span className="system-signal-value">{incident.ml_signals.language || 'N/A'}</span>
                </div>
                <div className="system-signal-item">
                  <span className="system-signal-label">Repetition:</span>
                  <span className="system-signal-value">{incident.ml_signals.repetition_count || 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Completeness */}
        {incident?.completeness !== undefined && (
          <div className="incident-field completeness-field">
            <div className="field-label">Completeness</div>
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
