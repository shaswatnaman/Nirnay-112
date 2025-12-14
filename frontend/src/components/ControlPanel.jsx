/**
 * ControlPanel component for call control actions.
 * 
 * This component provides buttons for:
 * - Take Over: Escalate to human operator
 * - End Call: Terminate the current call
 * - Mark Resolved: Mark incident as resolved
 * 
 * All actions trigger callback functions for handling.
 */

import React from 'react';
import './ControlPanel.css';

const ControlPanel = ({ 
  onTakeOver = () => {},
  onEndCall = () => {},
  onMarkResolved = () => {},
  disabled = false
}) => {
  /**
   * Handle Take Over button click.
   * 
   * Triggers escalation to human operator.
   */
  const handleTakeOver = () => {
    if (disabled) return;
    
    if (window.confirm('Are you sure you want to take over this call? A human operator will be assigned.')) {
      onTakeOver();
    }
  };

  /**
   * Handle End Call button click.
   * 
   * Terminates the current call session.
   */
  const handleEndCall = () => {
    if (disabled) return;
    
    if (window.confirm('Are you sure you want to end this call?')) {
      onEndCall();
    }
  };

  /**
   * Handle Mark Resolved button click.
   * 
   * Marks the incident as resolved.
   */
  const handleMarkResolved = () => {
    if (disabled) return;
    
    if (window.confirm('Mark this incident as resolved?')) {
      onMarkResolved();
    }
  };

  return (
    <div className="control-panel">
      <div className="control-panel-header">
        <h3>Call Controls</h3>
      </div>

      <div className="control-buttons">
        {/* Take Over Button */}
        <button
          className="control-button button-take-over"
          onClick={handleTakeOver}
          disabled={disabled}
          title="Escalate to human operator"
        >
          <span className="button-icon">👤</span>
          <span className="button-text">Take Over</span>
        </button>

        {/* End Call Button */}
        <button
          className="control-button button-end-call"
          onClick={handleEndCall}
          disabled={disabled}
          title="End the current call"
        >
          <span className="button-icon">📞</span>
          <span className="button-text">End Call</span>
        </button>

        {/* Mark Resolved Button */}
        <button
          className="control-button button-mark-resolved"
          onClick={handleMarkResolved}
          disabled={disabled}
          title="Mark incident as resolved"
        >
          <span className="button-icon">✅</span>
          <span className="button-text">Mark Resolved</span>
        </button>
      </div>

      {disabled && (
        <div className="control-disabled-message">
          <span>Controls disabled</span>
        </div>
      )}
    </div>
  );
};

export default ControlPanel;

