/**
 * Main App component for Emergency Dispatcher Console.
 * 
 * Professional multi-panel layout for emergency call triage:
 * - Live transcript panel (streaming conversation)
 * - Incident details panel (structured fields)
 * - Escalation panel (urgency, escalation state)
 * - System status panel (connection, health)
 * - Control panel (actions)
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import socketService from './services/socket';
import LiveTranscript from './components/LiveTranscript';
import IncidentPanel from './components/IncidentPanel';
import EscalationPanel from './components/EscalationPanel';
import SystemStatusPanel from './components/SystemStatusPanel';
import ControlPanel from './components/ControlPanel';
import './App.css';

function App() {
  // Core state
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);
  
  // Transcript state
  const [transcripts, setTranscripts] = useState([]);
  
  // Incident state
  const [incident, setIncident] = useState(null);
  
  // Escalation state
  const [escalationState, setEscalationState] = useState('normal');
  const [urgencyScore, setUrgencyScore] = useState(null);
  const [urgencyLevel, setUrgencyLevel] = useState(null);
  const [escalationReason, setEscalationReason] = useState(null);
  const [decisionExplanation, setDecisionExplanation] = useState(null);
  
  // System status state
  const [lastUpdate, setLastUpdate] = useState(null);
  const [transcriptionStatus, setTranscriptionStatus] = useState(null);

  // Refs for audio handling
  const mediaStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const intervalRef = useRef(null);

  /**
   * Initialize WebSocket connection and handle all message types.
   */
  useEffect(() => {
    const handleWebSocketEvent = (event) => {
      setLastUpdate(new Date().toISOString());
      
      switch (event.type) {
        case 'connected':
        case 'session_initialized':
          setIsConnected(true);
          setSessionId(event.sessionId || socketService.getSessionId());
          setError(null);
          break;

        case 'disconnected':
          setIsConnected(false);
          break;

        case 'transcript':
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

        case 'incident_summary':
        case 'incident':
          const incidentData = event.incident || event.summary || event;
          const fullIncident = {
            ...incidentData,
            incident: incidentData.incident || incidentData,
            confidence: event.confidence,
            missing_fields: event.missing_fields || []
          };
          setIncident(fullIncident);
          
          // Update escalation state from incident data
          const incidentInfo = incidentData.incident || incidentData;
          if (incidentInfo.human_required) {
            setEscalationState('escalate');
            setEscalationReason(incidentInfo.escalation_reason || 'System escalation');
          } else {
            setEscalationState('normal');
            setEscalationReason(null);
          }
          
          // Update urgency from incident data
          if (incidentInfo.urgency_score !== undefined) {
            setUrgencyScore(incidentInfo.urgency_score);
          }
          if (incidentInfo.urgency !== undefined || incidentInfo.urgency_level !== undefined) {
            setUrgencyLevel(incidentInfo.urgency || incidentInfo.urgency_level);
          }
          break;

        case 'decision_explanation':
          setDecisionExplanation(event);
          if (event.urgency_score !== undefined) {
            setUrgencyScore(event.urgency_score);
          }
          if (event.urgency_level !== undefined) {
            setUrgencyLevel(event.urgency_level);
          }
          if (event.why_escalated) {
            setEscalationState('escalate');
            setEscalationReason(event.why_escalated);
          }
          break;

        case 'transcription_status':
          setTranscriptionStatus(event.status || 'ok');
          if (event.status !== 'ok') {
            setError(`Transcription ${event.status}: ${event.message || event.reason || 'Unknown error'}`);
          }
          break;

        case 'error':
          setError(event.message || 'An error occurred');
          break;

        default:
          // Silently ignore unknown events
          break;
      }
    };

    socketService.subscribe(handleWebSocketEvent);
    socketService.connect().catch((err) => {
      setError('Failed to connect to server');
    });

    return () => {
      socketService.unsubscribe(handleWebSocketEvent);
      stopRecording();
      socketService.disconnect();
    };
  }, []);

  /**
   * Start microphone recording and streaming.
   */
  const startRecording = useCallback(async () => {
    try {
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
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(8192, 1, 1);
      processorRef.current = processor;

      let audioBuffer = [];
      let isRecordingActive = true;
      
      processor.onaudioprocess = (event) => {
        if (!isRecordingActive) return;

        const inputData = event.inputBuffer.getChannelData(0);
        audioBuffer.push(...Array.from(inputData));

        const chunkSize = 8000; // 500ms at 16kHz
        if (audioBuffer.length >= chunkSize) {
          const chunk = audioBuffer.splice(0, chunkSize);
          const float32Chunk = new Float32Array(chunk);
          socketService.sendAudioChunk(float32Chunk);
        }
      };
      
      processor._stopRecording = () => {
        isRecordingActive = false;
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
    } catch (error) {
      setError(`Failed to access microphone: ${error.message}`);
    }
  }, []);

  /**
   * Stop microphone recording and cleanup.
   */
  const stopRecording = useCallback(() => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (processorRef.current) {
      if (processorRef.current._stopRecording) {
        processorRef.current._stopRecording();
      }
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    setIsRecording(false);
  }, []);

  /**
   * Toggle recording state.
   */
  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  /**
   * Handle Escalate action.
   */
  const handleEscalate = useCallback(() => {
    if (socketService.getConnectionStatus()) {
      socketService.ws?.send(JSON.stringify({
        type: 'escalate',
        session_id: sessionId,
        reason: 'Manual escalation'
      }));
    }
    setEscalationState('escalate');
    setEscalationReason('Manual escalation');
    setIncident((prev) => ({
      ...prev,
      human_required: true,
      escalation_reason: 'Manual escalation'
    }));
  }, [sessionId]);

  /**
   * Handle End Call action.
   */
  const handleEndCall = useCallback(() => {
    stopRecording();
    socketService.disconnect();
    setIsConnected(false);
    setTranscripts([]);
    setIncident(null);
    setSessionId(null);
    setEscalationState('normal');
    setUrgencyScore(null);
    setUrgencyLevel(null);
    setEscalationReason(null);
    setDecisionExplanation(null);
  }, [stopRecording]);

  /**
   * Handle Resolve action.
   */
  const handleResolve = useCallback(() => {
    if (socketService.getConnectionStatus()) {
      socketService.ws?.send(JSON.stringify({
        type: 'resolve',
        session_id: sessionId
      }));
    }
  }, [sessionId]);

  return (
    <div className="app">
      {/* Header */}
      <div className="app-header">
        <div className="header-left">
          <h1>Emergency Dispatcher Console</h1>
          {sessionId && (
            <div className="session-info">
              Session: {sessionId.substring(0, 8)}...
            </div>
          )}
        </div>
        <SystemStatusPanel
          isConnected={isConnected}
          sessionId={sessionId}
          lastUpdate={lastUpdate}
          transcriptionStatus={transcriptionStatus}
          isRecording={isRecording}
        />
      </div>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss error">×</button>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="app-content">
        {/* Left: Transcript Panel (60% width) */}
        <div className="content-panel transcript-panel">
          <LiveTranscript transcripts={transcripts} />
        </div>

        {/* Middle: Incident Details Panel (20% width) */}
        <div className="content-panel incident-panel">
          <IncidentPanel incident={incident} />
        </div>

        {/* Right: Escalation Panel (20% width) */}
        <div className="content-panel escalation-panel">
          <EscalationPanel
            escalationState={escalationState}
            urgencyScore={urgencyScore}
            urgencyLevel={urgencyLevel}
            escalationReason={escalationReason}
            decisionExplanation={decisionExplanation}
          />
        </div>
      </div>

      {/* Bottom: Control Panel */}
      <div className="app-footer">
        <ControlPanel
          onEscalate={handleEscalate}
          onEndCall={handleEndCall}
          onResolve={handleResolve}
          disabled={!isConnected}
        />
        <div className="recording-control">
          <button
            className={`record-button ${isRecording ? 'recording' : ''}`}
            onClick={toggleRecording}
            disabled={!isConnected}
            title={isRecording ? 'Stop Recording' : 'Start Recording'}
          >
            <span className="record-text">
              {isRecording ? 'Stop Recording' : 'Start Recording'}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
