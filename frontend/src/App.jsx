/**
 * Main App component for Nirnay emergency response system.
 * 
 * This component integrates:
 * - LiveTranscript: Real-time conversation display
 * - IncidentPanel: Incident information display
 * - ControlPanel: Call control actions
 * - WebSocket service: Real-time communication
 * - Microphone streaming: Audio capture and transmission
 * - Audio playback: AI response audio
 * 
 * Features:
 * - Microphone streaming in 500ms chunks
 * - Real-time transcript updates
 * - Live incident information updates
 * - Automatic AI audio playback
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import socketService from './services/socket';
import LiveTranscript from './components/LiveTranscript';
import IncidentPanel from './components/IncidentPanel';
import ControlPanel from './components/ControlPanel';
import './App.css';

function App() {
  // State management
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [transcripts, setTranscripts] = useState([]);
  const [incident, setIncident] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);

  // Refs for audio handling
  const mediaStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const intervalRef = useRef(null);

  /**
   * Initialize WebSocket connection on component mount.
   * 
   * Sets up event handlers for:
   * - Connection status
   * - Transcript updates
   * - Incident updates
   * - Audio chunks
   * - Errors
   */
  useEffect(() => {
    // WebSocket event handler
    const handleWebSocketEvent = (event) => {
      switch (event.type) {
        case 'connected':
        case 'session_initialized':
          setIsConnected(true);
          setSessionId(event.sessionId || socketService.getSessionId());
          setError(null);
          console.log('WebSocket connected, session:', event.sessionId);
          break;

        case 'disconnected':
          setIsConnected(false);
          console.log('WebSocket disconnected');
          break;

        case 'transcript':
          // Add new transcript to list
          setTranscripts((prev) => [
            ...prev,
            {
              text: event.text,
              speaker: event.speaker,
              timestamp: event.timestamp,
              confidence: event.confidence,
              isPartial: false
            }
          ]);
          break;

        case 'incident':
          // Update incident information
          setIncident(event.incident || event);
          console.log('Incident updated:', event.incident);
          break;

        case 'error':
          setError(event.message || 'An error occurred');
          console.error('WebSocket error:', event);
          break;

        default:
          console.log('Unhandled WebSocket event:', event.type);
      }
    };

    // Subscribe to WebSocket events
    socketService.subscribe(handleWebSocketEvent);

    // Connect to WebSocket
    socketService.connect().catch((err) => {
      console.error('Failed to connect:', err);
      setError('Failed to connect to server');
    });

    // Cleanup on unmount
    return () => {
      socketService.unsubscribe(handleWebSocketEvent);
      stopRecording();
      socketService.disconnect();
    };
  }, []);

  /**
   * Start microphone recording and streaming.
   * 
   * Captures audio from user's microphone and sends it to backend
   * in 500ms chunks via WebSocket for real-time transcription.
   */
  const startRecording = useCallback(async () => {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      mediaStreamRef.current = stream;

      // Create AudioContext for processing
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      // Create audio source from microphone
      const source = audioContext.createMediaStreamSource(stream);

      // Create script processor for chunking
      // Note: ScriptProcessorNode is deprecated but widely supported
      // For production, consider using AudioWorkletNode
      const processor = audioContext.createScriptProcessor(8192, 1, 1);
      processorRef.current = processor;

      // Buffer for accumulating audio data
      let audioBuffer = [];

      // Process audio chunks
      processor.onaudioprocess = (event) => {
        if (!isRecording) return;

        // Get audio data (Float32Array)
        const inputData = event.inputBuffer.getChannelData(0);

        // Accumulate audio data
        audioBuffer.push(...Array.from(inputData));

        // Send chunks every 500ms (8000 samples at 16kHz = 500ms)
        const chunkSize = 8000; // 500ms at 16kHz
        if (audioBuffer.length >= chunkSize) {
          // Extract chunk
          const chunk = audioBuffer.splice(0, chunkSize);
          const float32Chunk = new Float32Array(chunk);

          // Send to backend via WebSocket
          socketService.sendAudioChunk(float32Chunk);
        }
      };

      // Connect processor
      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
      console.log('Recording started');
    } catch (error) {
      console.error('Error starting recording:', error);
      setError(`Failed to access microphone: ${error.message}`);
    }
  }, [isRecording]);

  /**
   * Stop microphone recording and cleanup.
   * 
   * Stops audio capture and releases resources.
   */
  const stopRecording = useCallback(() => {
    // Stop media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Disconnect processor
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    // Clear interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    setIsRecording(false);
    console.log('Recording stopped');
  }, []);

  /**
   * Toggle recording state.
   * 
   * Starts or stops microphone recording based on current state.
   */
  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  /**
   * Handle Take Over action.
   * 
   * Escalates call to human operator.
   */
  const handleTakeOver = useCallback(() => {
    console.log('Take Over requested');
    // Send escalation message to backend
    if (socketService.getConnectionStatus()) {
      socketService.ws?.send(JSON.stringify({
        type: 'escalate',
        session_id: sessionId,
        reason: 'Manual escalation'
      }));
    }
    // Update UI to show human required
    setIncident((prev) => ({
      ...prev,
      human_required: true,
      escalation_reason: 'Manual escalation'
    }));
  }, [sessionId]);

  /**
   * Handle End Call action.
   * 
   * Terminates the current call session.
   */
  const handleEndCall = useCallback(() => {
    console.log('End Call requested');
    stopRecording();
    socketService.disconnect();
    setIsConnected(false);
    // Reset state
    setTranscripts([]);
    setIncident(null);
    setSessionId(null);
  }, [stopRecording]);

  /**
   * Handle Mark Resolved action.
   * 
   * Marks the incident as resolved.
   */
  const handleMarkResolved = useCallback(() => {
    console.log('Mark Resolved requested');
    // Send resolution message to backend
    if (socketService.getConnectionStatus()) {
      socketService.ws?.send(JSON.stringify({
        type: 'resolve',
        session_id: sessionId
      }));
    }
  }, [sessionId]);

  return (
    <div className="app">
      <div className="app-header">
        <h1>Nirnay Emergency Response System</h1>
        <div className="status-indicators">
          <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot" />
            <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
          <div className={`status-indicator ${isRecording ? 'recording' : 'idle'}`}>
            <span className="status-dot" />
            <span>{isRecording ? 'Recording' : 'Idle'}</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <div className="app-content">
        {/* Left Column: Transcript */}
        <div className="content-column transcript-column">
          <LiveTranscript transcripts={transcripts} />
        </div>

        {/* Right Column: Incident & Controls */}
        <div className="content-column sidebar-column">
          <div className="sidebar-content">
            <IncidentPanel incident={incident} />
            <ControlPanel
              onTakeOver={handleTakeOver}
              onEndCall={handleEndCall}
              onMarkResolved={handleMarkResolved}
              disabled={!isConnected}
            />
          </div>
        </div>
      </div>

      {/* Recording Control */}
      <div className="recording-control">
        <button
          className={`record-button ${isRecording ? 'recording' : ''}`}
          onClick={toggleRecording}
          disabled={!isConnected}
          title={isRecording ? 'Stop Recording' : 'Start Recording'}
        >
          <span className="record-icon">
            {isRecording ? '⏹️' : '🎤'}
          </span>
          <span className="record-text">
            {isRecording ? 'Stop Recording' : 'Start Recording'}
          </span>
        </button>
      </div>
    </div>
  );
}

export default App;

