/**
 * EscalationPanel component for displaying escalation state and urgency information.
 * 
 * This component shows:
 * - Escalation status (Normal/Review/Escalate)
 * - Urgency score (numeric 0.0-1.0)
 * - Urgency level
 * - Escalation reason (if escalated)
 * - Decision explanation data (contributing factors)
 */

import React from 'react';
import './EscalationPanel.css';

const EscalationPanel = ({ 
  escalationState = 'normal',
  urgencyScore = null,
  urgencyLevel = null,
  escalationReason = null,
  decisionExplanation = null
}) => {
  /**
   * Get escalation status display.
   */
  const getEscalationStatus = () => {
    if (escalationState === 'escalate' || escalationState === 'escalated') {
      return { label: 'ESCALATE', class: 'escalate', color: 'var(--color-critical)' };
    } else if (escalationState === 'review') {
      return { label: 'REVIEW', class: 'review', color: 'var(--color-warning)' };
    }
    return { label: 'NORMAL', class: 'normal', color: 'var(--color-stable)' };
  };

  /**
   * Format urgency score for display.
   */
  const formatUrgencyScore = (score) => {
    if (score === null || score === undefined) return 'N/A';
    return score.toFixed(2);
  };

  /**
   * Get urgency level label.
   */
  const getUrgencyLevelLabel = (level) => {
    if (!level) return 'Unknown';
    const labels = {
      'critical': 'Critical',
      'high': 'High',
      'medium': 'Medium',
      'low': 'Low'
    };
    return labels[level.toLowerCase()] || level;
  };

  const status = getEscalationStatus();

  return (
    <div className="escalation-panel">
      <div className="panel-header">
        <h2>Escalation Status</h2>
      </div>

      <div className="escalation-content">
        {/* Escalation Status */}
        <div className="escalation-status-section">
          <div className="status-label">Status</div>
          <div className={`status-badge status-${status.class}`} style={{ borderColor: status.color }}>
            <span className="status-indicator-dot" style={{ backgroundColor: status.color }} />
            <span className="status-text">{status.label}</span>
          </div>
        </div>

        {/* Urgency Score */}
        <div className="escalation-field">
          <div className="field-label">Urgency Score</div>
          <div className="field-value urgency-score-value">
            {formatUrgencyScore(urgencyScore)}
            {urgencyScore !== null && urgencyScore !== undefined && (
              <span className="score-range">/ 1.00</span>
            )}
          </div>
        </div>

        {/* Urgency Level */}
        <div className="escalation-field">
          <div className="field-label">Urgency Level</div>
          <div className="field-value">
            {urgencyLevel ? (
              <span className={`urgency-level-badge urgency-${urgencyLevel.toLowerCase()}`}>
                {getUrgencyLevelLabel(urgencyLevel)}
              </span>
            ) : (
              <span className="field-empty">Unknown</span>
            )}
          </div>
        </div>

        {/* Escalation Reason */}
        {escalationReason && (
          <div className="escalation-field">
            <div className="field-label">Escalation Reason</div>
            <div className="field-value escalation-reason">
              {escalationReason}
            </div>
          </div>
        )}

        {/* Decision Explanation - Contributing Factors */}
        {decisionExplanation && decisionExplanation.top_3_contributing_factors && (
          <div className="escalation-field">
            <div className="field-label">Contributing Factors</div>
            <div className="field-value">
              <ul className="contributing-factors">
                {decisionExplanation.top_3_contributing_factors.map((factor, index) => (
                  <li key={index}>{factor}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Decision Explanation - Why Escalated */}
        {decisionExplanation && decisionExplanation.why_escalated && (
          <div className="escalation-field">
            <div className="field-label">Escalation Trigger</div>
            <div className="field-value escalation-trigger">
              {decisionExplanation.why_escalated}
            </div>
          </div>
        )}

        {/* Confidence Warnings */}
        {decisionExplanation && decisionExplanation.confidence_warnings && 
         decisionExplanation.confidence_warnings.length > 0 && (
          <div className="escalation-field">
            <div className="field-label">Confidence Warnings</div>
            <div className="field-value">
              <ul className="confidence-warnings">
                {decisionExplanation.confidence_warnings.map((warning, index) => (
                  <li key={index} className="warning-item">{warning}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EscalationPanel;

