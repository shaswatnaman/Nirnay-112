/**
 * WebSocket client service for real-time communication with backend.
 * 
 * This service handles:
 * - WebSocket connection to /ws/call endpoint
 * - Sending audio chunks to backend
 * - Receiving AI audio, transcripts, and incident updates
 * - Managing connection state and error handling
 */

class WebSocketService {
  constructor() {
    this.ws = null;
    this.sessionId = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second
    this.subscribers = new Set(); // Set of callback functions
    this.audioContext = null;
    this.audioQueue = []; // Queue for audio chunks
    this.isPlaying = false;
  }

  /**
   * Connect to WebSocket server at /ws/call endpoint.
   * 
   * Establishes WebSocket connection and sends session initialization.
   * Handles reconnection logic on connection failure.
   * 
   * @param {string} sessionId - Optional session ID (generated if not provided)
   * @returns {Promise<void>} Resolves when connected
   */
  async connect(sessionId = null) {
    // Generate session ID if not provided
    if (!sessionId) {
      sessionId = this.generateSessionId();
    }
    this.sessionId = sessionId;

    return new Promise((resolve, reject) => {
      try {
        // Determine WebSocket URL based on environment
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = window.location.port || (protocol === 'wss:' ? '443' : '80');
        const wsUrl = `${protocol}//${host}:${port}/ws/call`;

        // Create WebSocket connection
        this.ws = new WebSocket(wsUrl);

        // Connection opened
        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.reconnectDelay = 1000;

          // Send session initialization message
          this.ws.send(JSON.stringify({
            type: 'session_init',
            session_id: this.sessionId
          }));

          this.notifySubscribers({
            type: 'connected',
            sessionId: this.sessionId
          });

          resolve();
        };

        // Handle incoming messages
        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        // Handle connection errors
        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.notifySubscribers({
            type: 'error',
            message: 'WebSocket connection error',
            error: error
          });
          reject(error);
        };

        // Handle connection close
        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          this.isConnected = false;

          this.notifySubscribers({
            type: 'disconnected',
            code: event.code,
            reason: event.reason
          });

          // Attempt reconnection if not intentional close
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };
      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        reject(error);
      }
    });
  }

  /**
   * Attempt to reconnect to WebSocket server.
   * 
   * Uses exponential backoff for reconnection delays.
   */
  attemptReconnect() {
    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);

    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms...`);

    setTimeout(() => {
      this.connect(this.sessionId).catch((error) => {
        console.error('Reconnection failed:', error);
      });
    }, delay);
  }

  /**
   * Handle incoming WebSocket messages.
   * 
   * Processes different message types:
   * - Binary: AI audio chunks
   * - Text: JSON messages (transcripts, incident updates, errors)
   * 
   * @param {MessageEvent} event - WebSocket message event
   */
  handleMessage(event) {
    // Binary message = AI audio chunk
    if (event.data instanceof ArrayBuffer || event.data instanceof Blob) {
      this.handleAudioChunk(event.data);
      return;
    }

    // Text message = JSON data
    try {
      const message = JSON.parse(event.data);
      this.processMessage(message);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
      this.notifySubscribers({
        type: 'error',
        message: 'Failed to parse message',
        error: error
      });
    }
  }

  /**
   * Process parsed JSON messages.
   * 
   * Handles different message types:
   * - session_initialized: Session confirmation
   * - transcript: User or AI transcript update
   * - incident_summary: Incident information update
   * - error: Error messages
   * 
   * @param {Object} message - Parsed JSON message
   */
  processMessage(message) {
    switch (message.type) {
      case 'session_initialized':
        console.log('Session initialized:', message.session_id);
        this.notifySubscribers({
          type: 'session_initialized',
          sessionId: message.session_id
        });
        break;

      case 'transcript':
      case 'user_transcript':
      case 'ai_transcript':
        // Transcript update
        this.notifySubscribers({
          type: 'transcript',
          text: message.text,
          speaker: message.speaker || (message.type === 'ai_transcript' ? 'ai' : 'user'),
          timestamp: message.timestamp || new Date().toISOString(),
          confidence: message.confidence
        });
        break;

      case 'incident_summary':
        // Incident information update
        this.notifySubscribers({
          type: 'incident',
          incident: message.summary || message.incident,
          confidence: message.confidence,
          missing_fields: message.missing_fields || []
        });
        break;

      case 'error':
        console.error('Server error:', message.message);
        this.notifySubscribers({
          type: 'error',
          message: message.message,
          error: message
        });
        break;

      case 'audio_processed':
        // Audio chunk processed acknowledgment
        this.notifySubscribers({
          type: 'audio_processed',
          transcribed: message.transcribed || false
        });
        break;

      default:
        console.log('Unknown message type:', message.type);
        this.notifySubscribers({
          type: 'unknown',
          message: message
        });
    }
  }

  /**
   * Handle incoming AI audio chunks.
   * 
   * Queues audio chunks and plays them sequentially for smooth playback.
   * 
   * @param {ArrayBuffer|Blob} audioData - Binary audio data
   */
  async handleAudioChunk(audioData) {
    try {
      // Convert Blob to ArrayBuffer if needed
      const arrayBuffer = audioData instanceof Blob 
        ? await audioData.arrayBuffer() 
        : audioData;

      // Initialize AudioContext if needed
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }

      // Decode audio data
      const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

      // Queue audio for playback
      this.audioQueue.push(audioBuffer);

      // Start playing if not already playing
      if (!this.isPlaying) {
        this.playAudioQueue();
      }

      // Notify subscribers about audio chunk
      this.notifySubscribers({
        type: 'audio_chunk',
        data: arrayBuffer
      });
    } catch (error) {
      console.error('Error handling audio chunk:', error);
      this.notifySubscribers({
        type: 'error',
        message: 'Failed to process audio chunk',
        error: error
      });
    }
  }

  /**
   * Play queued audio chunks sequentially.
   * 
   * Ensures smooth playback by playing chunks in order.
   */
  async playAudioQueue() {
    if (this.isPlaying || this.audioQueue.length === 0) {
      return;
    }

    this.isPlaying = true;

    while (this.audioQueue.length > 0) {
      const audioBuffer = this.audioQueue.shift();
      
      try {
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.audioContext.destination);

        await new Promise((resolve) => {
          source.onended = resolve;
          source.start(0);
        });
      } catch (error) {
        console.error('Error playing audio:', error);
      }
    }

    this.isPlaying = false;
  }

  /**
   * Send audio chunk to backend for transcription.
   * 
   * Sends binary audio data to WebSocket server for processing.
   * 
   * @param {ArrayBuffer|Blob|Float32Array} chunk - Audio chunk data
   */
  sendAudioChunk(chunk) {
    if (!this.isConnected || !this.ws) {
      console.warn('WebSocket not connected, cannot send audio chunk');
      return;
    }

    try {
      // Convert Float32Array to Int16Array if needed
      let audioData = chunk;
      
      if (chunk instanceof Float32Array) {
        // Convert float32 to int16 for transmission
        const int16Array = new Int16Array(chunk.length);
        for (let i = 0; i < chunk.length; i++) {
          const s = Math.max(-1, Math.min(1, chunk[i]));
          int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        audioData = int16Array.buffer;
      } else if (chunk instanceof ArrayBuffer) {
        audioData = chunk;
      } else if (chunk instanceof Blob) {
        audioData = chunk;
      } else {
        console.error('Unsupported audio chunk type:', typeof chunk);
        return;
      }

      // Send binary data
      this.ws.send(audioData);
    } catch (error) {
      console.error('Error sending audio chunk:', error);
      this.notifySubscribers({
        type: 'error',
        message: 'Failed to send audio chunk',
        error: error
      });
    }
  }

  /**
   * Subscribe to WebSocket events.
   * 
   * Adds a callback function that will be called for all WebSocket events.
   * 
   * @param {Function} callback - Callback function to receive events
   */
  subscribe(callback) {
    if (typeof callback === 'function') {
      this.subscribers.add(callback);
    } else {
      console.warn('subscribe: callback must be a function');
    }
  }

  /**
   * Unsubscribe from WebSocket events.
   * 
   * Removes a callback function from subscribers.
   * 
   * @param {Function} callback - Callback function to remove
   */
  unsubscribe(callback) {
    this.subscribers.delete(callback);
  }

  /**
   * Notify all subscribers of an event.
   * 
   * Calls all subscribed callback functions with the event data.
   * 
   * @param {Object} event - Event data to send to subscribers
   */
  notifySubscribers(event) {
    this.subscribers.forEach((callback) => {
      try {
        callback(event);
      } catch (error) {
        console.error('Error in subscriber callback:', error);
      }
    });
  }

  /**
   * Disconnect from WebSocket server.
   * 
   * Closes the connection and cleans up resources.
   */
  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.isConnected = false;
    this.audioQueue = [];
    this.isPlaying = false;
    
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }

  /**
   * Generate a unique session ID.
   * 
   * @returns {string} Unique session identifier
   */
  generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get current connection status.
   * 
   * @returns {boolean} True if connected, false otherwise
   */
  getConnectionStatus() {
    return this.isConnected;
  }

  /**
   * Get current session ID.
   * 
   * @returns {string|null} Session ID or null if not connected
   */
  getSessionId() {
    return this.sessionId;
  }
}

// Export singleton instance
const socketService = new WebSocketService();
export default socketService;

