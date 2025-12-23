/**
 * ControlPanel component for call control actions.
 * 
 * Provides buttons for:
 * - Escalate: Escalate to human operator
 * - End Call: Terminate the current call
 * - Resolve: Mark incident as resolved
 */

import React from 'react';
import './ControlPanel.css';

const ControlPanel = ({ 
  onEscalate = () => {},
  onEndCall = () => {},
  onResolve = () => {},
  disabled = false
}) => {
  /**
   * Handle Escalate button click.
   */
  const handleEscalate = () => {
    if (disabled) return;
    
    if (window.confirm('Escalate this call to human operator?')) {
      onEscalate();
    }
  };

  /**
   * Handle End Call button click.
   */
  const handleEndCall = () => {
    if (disabled) return;
    
    if (window.confirm('End this call session?')) {
      onEndCall();
    }
  };

  /**
   * Handle Resolve button click.
   */
  const handleResolve = () => {
    if (disabled) return;
    
    if (window.confirm('Mark this incident as resolved?')) {
      onResolve();
    }
  };

  return (
    <div className="control-panel">
      <div className="control-panel-header">
        <h3>Call Controls</h3>
      </div>

      <div className="control-buttons">
        {/* Escalate Button */}
        <button
          className="control-button button-escalate"
          onClick={handleEscalate}
          disabled={disabled}
          title="Escalate to human operator"
        >
          <span className="button-text">Escalate</span>
        </button>

        {/* End Call Button */}
        <button
          className="control-button button-end-call"
          onClick={handleEndCall}
          disabled={disabled}
          title="End the current call"
        >
          <span className="button-text">End Call</span>
        </button>

        {/* Resolve Button */}
        <button
          className="control-button button-resolve"
          onClick={handleResolve}
          disabled={disabled}
          title="Mark incident as resolved"
        >
          <span className="button-text">Resolve</span>
        </button>
      </div>

      {disabled && (
        <div className="control-disabled-message">
          <span>Controls disabled - not connected</span>
        </div>
      )}
    </div>
  );
};

export default ControlPanel;
