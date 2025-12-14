/**
 * LiveTranscript component for displaying real-time conversation transcripts.
 * 
 * This component shows user and AI speech in separate columns with:
 * - Real-time streaming updates
 * - Partial transcript support (shows incomplete sentences)
 * - Auto-scrolling to latest messages
 * - Visual distinction between user and AI messages
 */

import React, { useState, useEffect, useRef } from 'react';
import './LiveTranscript.css';

const LiveTranscript = ({ transcripts = [] }) => {
  // State for managing transcripts
  const [userTranscripts, setUserTranscripts] = useState([]);
  const [aiTranscripts, setAiTranscripts] = useState([]);
  
  // Refs for auto-scrolling
  const userScrollRef = useRef(null);
  const aiScrollRef = useRef(null);
  const shouldAutoScroll = useRef(true);

  /**
   * Update transcripts when new data arrives.
   * 
   * Handles both complete and partial transcripts for streaming support.
   */
  useEffect(() => {
    if (!transcripts || transcripts.length === 0) {
      return;
    }

    // Separate user and AI transcripts
    const userMessages = [];
    const aiMessages = [];

    transcripts.forEach((transcript) => {
      const message = {
        text: transcript.text || '',
        timestamp: transcript.timestamp || new Date().toISOString(),
        confidence: transcript.confidence,
        isPartial: transcript.isPartial || false
      };

      if (transcript.speaker === 'user') {
        userMessages.push(message);
      } else if (transcript.speaker === 'ai') {
        aiMessages.push(message);
      }
    });

    // Update state
    setUserTranscripts(userMessages);
    setAiTranscripts(aiMessages);

    // Auto-scroll to bottom
    if (shouldAutoScroll.current) {
      scrollToBottom();
    }
  }, [transcripts]);

  /**
   * Scroll both columns to bottom.
   * 
   * Called when new messages arrive to keep latest content visible.
   */
  const scrollToBottom = () => {
    setTimeout(() => {
      if (userScrollRef.current) {
        userScrollRef.current.scrollTop = userScrollRef.current.scrollHeight;
      }
      if (aiScrollRef.current) {
        aiScrollRef.current.scrollTop = aiScrollRef.current.scrollHeight;
      }
    }, 100);
  };

  /**
   * Handle scroll events to disable auto-scroll if user scrolls up.
   * 
   * Allows users to read older messages without being forced to bottom.
   */
  const handleScroll = (ref, event) => {
    const element = event.target;
    const isAtBottom = element.scrollHeight - element.scrollTop <= element.clientHeight + 10;
    shouldAutoScroll.current = isAtBottom;
  };

  /**
   * Format timestamp for display.
   * 
   * @param {string} timestamp - ISO timestamp string
   * @returns {string} Formatted time string
   */
  const formatTime = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    } catch (error) {
      return '';
    }
  };

  /**
   * Render a single transcript message.
   * 
   * @param {Object} message - Transcript message object
   * @param {string} speaker - 'user' or 'ai'
   * @returns {JSX.Element} Message element
   */
  const renderMessage = (message, speaker) => {
    const isUser = speaker === 'user';
    const confidence = message.confidence !== undefined ? message.confidence : null;

    return (
      <div 
        key={`${message.timestamp}-${message.text}`}
        className={`transcript-message ${isUser ? 'user-message' : 'ai-message'} ${message.isPartial ? 'partial' : ''}`}
      >
        <div className="message-content">
          {message.text}
          {message.isPartial && <span className="partial-indicator">...</span>}
        </div>
        <div className="message-meta">
          <span className="message-time">{formatTime(message.timestamp)}</span>
          {confidence !== null && isUser && (
            <span className="message-confidence">
              Confidence: {(confidence * 100).toFixed(0)}%
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
          <span>AI: {aiTranscripts.length}</span>
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
            onScroll={(e) => handleScroll(userScrollRef, e)}
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

        {/* AI Transcript Column */}
        <div className="transcript-column ai-column">
          <div className="column-header">
            <h3>AI Assistant</h3>
          </div>
          <div 
            className="transcript-messages"
            ref={aiScrollRef}
            onScroll={(e) => handleScroll(aiScrollRef, e)}
          >
            {aiTranscripts.length === 0 ? (
              <div className="empty-transcript">
                <p>Waiting for AI response...</p>
              </div>
            ) : (
              aiTranscripts.map((message, index) => renderMessage(message, 'ai'))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveTranscript;

