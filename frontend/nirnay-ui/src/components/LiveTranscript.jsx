/**
 * LiveTranscript component for displaying real-time conversation transcripts.
 * 
 * Shows user and system speech in separate columns with:
 * - Real-time streaming updates
 * - Auto-scrolling to latest messages (scroll-locked unless manually paused)
 * - Visual distinction between user and system messages
 * - Transcription confidence indicators
 */

import React, { useState, useEffect, useRef } from 'react';
import './LiveTranscript.css';

const LiveTranscript = ({ transcripts = [] }) => {
  const [userTranscripts, setUserTranscripts] = useState([]);
  const [systemTranscripts, setSystemTranscripts] = useState([]);
  
  const userScrollRef = useRef(null);
  const systemScrollRef = useRef(null);
  const shouldAutoScroll = useRef(true);

  /**
   * Update transcripts when new data arrives.
   */
  useEffect(() => {
    if (!transcripts || transcripts.length === 0) {
      return;
    }

    const userMessages = [];
    const systemMessages = [];

    transcripts.forEach((transcript) => {
      const message = {
        text: transcript.text || '',
        timestamp: transcript.timestamp || new Date().toISOString(),
        confidence: transcript.confidence,
        isPartial: transcript.isPartial || false
      };

      if (transcript.speaker === 'user') {
        userMessages.push(message);
      } else if (transcript.speaker === 'ai' || transcript.speaker === 'system') {
        systemMessages.push(message);
      }
    });

    setUserTranscripts(userMessages);
    setSystemTranscripts(systemMessages);

    if (shouldAutoScroll.current) {
      scrollToBottom();
    }
  }, [transcripts]);

  /**
   * Scroll both columns to bottom.
   */
  const scrollToBottom = () => {
    setTimeout(() => {
      if (userScrollRef.current) {
        userScrollRef.current.scrollTop = userScrollRef.current.scrollHeight;
      }
      if (systemScrollRef.current) {
        systemScrollRef.current.scrollTop = systemScrollRef.current.scrollHeight;
      }
    }, 50);
  };

  /**
   * Handle scroll events to disable auto-scroll if user scrolls up.
   */
  const handleScroll = (event) => {
    const element = event.target;
    const isAtBottom = element.scrollHeight - element.scrollTop <= element.clientHeight + 10;
    shouldAutoScroll.current = isAtBottom;
  };

  /**
   * Format timestamp for display.
   */
  const formatTime = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit',
        hour12: false
      });
    } catch (error) {
      return '';
    }
  };

  /**
   * Render a single transcript message.
   */
  const renderMessage = (message, speaker) => {
    const isUser = speaker === 'user';
    const confidence = message.confidence !== undefined ? message.confidence : null;

    return (
      <div 
        key={`${message.timestamp}-${message.text}`}
        className={`transcript-message ${isUser ? 'user-message' : 'system-message'} ${message.isPartial ? 'partial' : ''}`}
      >
        <div className="message-content">
          {message.text}
          {message.isPartial && <span className="partial-indicator">...</span>}
        </div>
        <div className="message-meta">
          <span className="message-time">{formatTime(message.timestamp)}</span>
          {confidence !== null && isUser && (
            <span className="message-confidence">
              {(confidence * 100).toFixed(0)}%
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="live-transcript-container">
      <div className="transcript-header">
        <h2>Live Transcript</h2>
        <div className="transcript-stats">
          <span>User: {userTranscripts.length}</span>
          <span>System: {systemTranscripts.length}</span>
        </div>
      </div>

      <div className="transcript-columns">
        {/* User Transcript Column */}
        <div className="transcript-column user-column">
          <div className="column-header">
            <h3>User</h3>
          </div>
          <div 
            className="transcript-messages"
            ref={userScrollRef}
            onScroll={handleScroll}
          >
            {userTranscripts.length === 0 ? (
              <div className="empty-transcript">
                <p>Waiting for user speech...</p>
              </div>
            ) : (
              userTranscripts.map((message, index) => renderMessage(message, 'user'))
            )}
          </div>
        </div>

        {/* System Transcript Column */}
        <div className="transcript-column system-column">
          <div className="column-header">
            <h3>System</h3>
          </div>
          <div 
            className="transcript-messages"
            ref={systemScrollRef}
            onScroll={handleScroll}
          >
            {systemTranscripts.length === 0 ? (
              <div className="empty-transcript">
                <p>Waiting for system response...</p>
              </div>
            ) : (
              systemTranscripts.map((message, index) => renderMessage(message, 'system'))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveTranscript;
