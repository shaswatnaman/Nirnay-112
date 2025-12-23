/**
 * SystemStatusPanel component for displaying system health and connection status.
 * 
 * This component shows:
 * - Connection state (Connected/Disconnected/Reconnecting)
 * - Session ID
 * - Last update timestamp
 * - Transcription status
 * - System health indicators
 */

import React from 'react';
import './SystemStatusPanel.css';

const SystemStatusPanel = ({
  isConnected = false,
  sessionId = null,
  lastUpdate = null,
  transcriptionStatus = null,
  isRecording = false
}) => {
  /**
   * Format timestamp for display.
   */
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
    } catch (error) {
      return 'Invalid';
    }
  };

  /**
   * Get connection status display.
   */
  const getConnectionStatus = () => {
    if (isConnected) {
      return { label: 'Connected', class: 'connected', color: 'var(--color-stable)' };
    }
    return { label: 'Disconnected', class: 'disconnected', color: 'var(--color-critical)' };
  };

  /**
   * Get transcription status display.
   */
  const getTranscriptionStatus = () => {
    if (!transcriptionStatus) return null;
    
    const statusMap = {
      'ok': { label: 'OK', class: 'ok', color: 'var(--color-stable)' },
      'silence': { label: 'Silence', class: 'silence', color: 'var(--text-secondary)' },
      'api_error': { label: 'API Error', class: 'error', color: 'var(--color-critical)' },
      'filtered': { label: 'Filtered', class: 'filtered', color: 'var(--color-warning)' }
    };
    
    return statusMap[transcriptionStatus] || { label: transcriptionStatus, class: 'unknown', color: 'var(--text-secondary)' };
  };

  const connectionStatus = getConnectionStatus();
  const transcriptionStatusDisplay = getTranscriptionStatus();

  return (
    <div className="system-status-panel">
      <div className="panel-header">
        <h2>System Status</h2>
      </div>

      <div className="status-content">
        {/* Connection Status */}
        <div className="status-item">
          <div className="status-item-label">Connection</div>
          <div className="status-item-value">
            <span 
              className={`status-indicator-dot status-${connectionStatus.class}`}
              style={{ backgroundColor: connectionStatus.color }}
            />
            <span>{connectionStatus.label}</span>
          </div>
        </div>

        {/* Recording Status */}
        <div className="status-item">
          <div className="status-item-label">Recording</div>
          <div className="status-item-value">
            <span 
              className={`status-indicator-dot ${isRecording ? 'status-active' : 'status-inactive'}`}
              style={{ backgroundColor: isRecording ? 'var(--color-critical)' : 'var(--text-tertiary)' }}
            />
            <span>{isRecording ? 'Active' : 'Inactive'}</span>
          </div>
        </div>

        {/* Session ID */}
        {sessionId && (
          <div className="status-item">
            <div className="status-item-label">Session ID</div>
            <div className="status-item-value session-id">
              {sessionId.substring(0, 8)}...
            </div>
          </div>
        )}

        {/* Last Update */}
        {lastUpdate && (
          <div className="status-item">
            <div className="status-item-label">Last Update</div>
            <div className="status-item-value timestamp">
              {formatTimestamp(lastUpdate)}
            </div>
          </div>
        )}

        {/* Transcription Status */}
        {transcriptionStatusDisplay && (
          <div className="status-item">
            <div className="status-item-label">Transcription</div>
            <div className="status-item-value">
              <span 
                className={`status-indicator-dot status-${transcriptionStatusDisplay.class}`}
                style={{ backgroundColor: transcriptionStatusDisplay.color }}
              />
              <span>{transcriptionStatusDisplay.label}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SystemStatusPanel;

