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
    this.audioQueue = []; // Queue for audio chunks (legacy, not used for MP3)
    this.mp3Buffer = []; // Buffer for MP3 chunks from gTTS
    this.mp3PlayTimeout = null; // Timeout for playing accumulated MP3 chunks
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
        // Backend runs on port 8000, frontend on 5173
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        // Backend WebSocket is always on port 8000
        // In production, this could be configured via environment variable
        const backendPort = '8000';
        const wsUrl = `${protocol}//${host}:${backendPort}/ws/call`;
        
        console.log('Connecting to WebSocket:', wsUrl);

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
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:144',message:'handleMessage called',data:{isArrayBuffer:event.data instanceof ArrayBuffer,isBlob:event.data instanceof Blob,dataType:typeof event.data,dataLength:event.data?.byteLength||event.data?.length||'unknown',constructor:event.data?.constructor?.name},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    
    // Binary message = AI audio chunk
    // Check for binary data - WebSocket can send ArrayBuffer, Blob, or Buffer
    if (event.data instanceof ArrayBuffer || event.data instanceof Blob || (typeof event.data === 'object' && event.data.byteLength !== undefined)) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:149',message:'Binary message detected',data:{size:event.data.byteLength||event.data.size||'unknown',type:event.data.constructor?.name},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      this.handleAudioChunk(event.data);
      return;
    }

    // Text message = JSON data
    try {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:156',message:'Attempting JSON parse',data:{rawData:typeof event.data==='string'?event.data.substring(0,200):String(event.data).substring(0,200)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      const message = JSON.parse(event.data);
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:160',message:'JSON parsed successfully',data:{messageType:message.type,messageKeys:Object.keys(message)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      this.processMessage(message);
    } catch (error) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:164',message:'JSON parse failed',data:{error:error.message,rawData:typeof event.data==='string'?event.data.substring(0,200):String(event.data).substring(0,200)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
      // #endregion
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
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:176',message:'processMessage called',data:{messageType:message.type,messageKeys:Object.keys(message),messageStringified:JSON.stringify(message).substring(0,300)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
    // #endregion
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
          type: 'incident_summary',
          incident: message.summary || message.incident,
          confidence: message.confidence,
          missing_fields: message.missing_fields || []
        });
        break;

      case 'decision_explanation':
        // Decision explanation with urgency breakdown
        this.notifySubscribers({
          type: 'decision_explanation',
          urgency_score: message.urgency_score,
          urgency_level: message.urgency_level,
          top_3_contributing_factors: message.top_3_contributing_factors || [],
          why_escalated: message.why_escalated,
          confidence_warnings: message.confidence_warnings || []
        });
        break;

      case 'transcription_status':
        // Transcription status (ok, silence, api_error, filtered)
        this.notifySubscribers({
          type: 'transcription_status',
          status: message.status,
          message: message.message || message.reason,
          confidence: message.confidence
        });
        break;

      case 'error':
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
        // Silently ignore unknown message types
        break;
    }
  }

  /**
   * Handle incoming AI audio chunks.
   * 
   * gTTS returns MP3 format, so we need to handle it differently than raw PCM.
   * We accumulate MP3 chunks and play them using HTMLAudioElement.
   * 
   * @param {ArrayBuffer|Blob} audioData - Binary audio data (MP3 from gTTS)
   */
  async handleAudioChunk(audioData) {
    try {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:263',message:'handleAudioChunk called',data:{isBlob:audioData instanceof Blob,isArrayBuffer:audioData instanceof ArrayBuffer,dataType:typeof audioData,size:audioData.byteLength||audioData.size||'unknown'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
      // #endregion
      
      // Convert Blob to ArrayBuffer if needed
      const arrayBuffer = audioData instanceof Blob 
        ? await audioData.arrayBuffer() 
        : audioData;

      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:272',message:'Audio converted to ArrayBuffer',data:{bufferSize:arrayBuffer.byteLength},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
      // #endregion

      // gTTS returns MP3 format, not raw PCM
      // We need to accumulate chunks and play as MP3
      if (!this.mp3Buffer) {
        this.mp3Buffer = [];
      }
      
      // Add chunk to buffer
      this.mp3Buffer.push(new Uint8Array(arrayBuffer));
      
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:281',message:'Chunk added to buffer',data:{bufferLength:this.mp3Buffer.length,isPlaying:this.isPlaying},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
      // #endregion
      
      // Wait for chunks to accumulate, then play
      // Clear any existing timeout
      if (this.mp3PlayTimeout) {
        clearTimeout(this.mp3PlayTimeout);
      }
      
      // Set timeout to play after chunks stop arriving
      // This ensures we get all chunks before playing
      // Clear any existing timeout
      if (this.mp3PlayTimeout) {
        clearTimeout(this.mp3PlayTimeout);
      }
      
      this.mp3PlayTimeout = setTimeout(() => {
        if (!this.isPlaying && this.mp3Buffer && this.mp3Buffer.length > 0) {
          this.playMP3Buffer();
        }
      }, 300); // Wait 300ms after last chunk before playing (reduced for faster response)

      // Notify subscribers about audio chunk
      this.notifySubscribers({
        type: 'audio_chunk',
        data: arrayBuffer
      });
    } catch (error) {
      console.error('Error handling audio chunk:', error);
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:293',message:'Error handling audio chunk',data:{error:error.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
      // #endregion
      this.notifySubscribers({
        type: 'error',
        message: 'Failed to process audio chunk',
        error: error
      });
    }
  }

  /**
   * Play accumulated MP3 buffer using HTMLAudioElement.
   * This handles MP3 format from gTTS properly.
   */
  async playMP3Buffer() {
    if (this.isPlaying || !this.mp3Buffer || this.mp3Buffer.length === 0) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:306',message:'playMP3Buffer skipped',data:{isPlaying:this.isPlaying,bufferLength:this.mp3Buffer?.length||0},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
      // #endregion
      return;
    }

    this.isPlaying = true;

    try {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:313',message:'Starting MP3 playback',data:{chunkCount:this.mp3Buffer.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
      // #endregion
      
      // Combine all accumulated chunks into single MP3 blob
      const totalLength = this.mp3Buffer.reduce((sum, chunk) => sum + chunk.length, 0);
      const combined = new Uint8Array(totalLength);
      let offset = 0;
      for (const chunk of this.mp3Buffer) {
        combined.set(chunk, offset);
        offset += chunk.length;
      }
      
      // Clear buffer
      this.mp3Buffer = [];
      
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:327',message:'MP3 blob created',data:{totalSize:totalLength},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
      // #endregion
      
      // Create blob URL for MP3
      const blob = new Blob([combined], { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(blob);
      
      // Play using HTMLAudioElement (handles MP3 natively)
      const audio = new Audio(audioUrl);
      audio.volume = 1.0; // Ensure volume is at maximum
      audio.preload = 'auto'; // Preload audio for smoother playback
      audio.muted = false; // Explicitly unmute
      
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:365',message:'Audio element created',data:{volume:audio.volume,muted:audio.muted,blobSize:totalLength},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
      // #endregion
      
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:370',message:'Audio element configured',data:{volume:audio.volume,muted:audio.muted},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
      // #endregion
      
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:333',message:'Audio element created, attempting play',data:{audioUrl:audioUrl.substring(0,50)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
      // #endregion
      
      // Set up event handlers before attempting to play
      const playPromise = new Promise((resolve, reject) => {
        let resolved = false;
        
        audio.onended = () => {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:337',message:'Audio playback ended',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
          // #endregion
          URL.revokeObjectURL(audioUrl); // Clean up
          this.isPlaying = false; // Reset playing flag
          if (!resolved) {
            resolved = true;
            resolve();
          }
        };
        
        audio.onerror = (error) => {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:342',message:'Audio playback error',data:{error:error.message||'unknown'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
          // #endregion
          URL.revokeObjectURL(audioUrl); // Clean up
          this.isPlaying = false; // Reset playing flag on error
          console.error('Audio playback error:', error);
          if (!resolved) {
            resolved = true;
            reject(error);
          }
        };
        
        // Try to play - handle autoplay policy
        const playAttempt = audio.play();
        if (playAttempt !== undefined) {
          playAttempt
            .then(() => {
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:349',message:'Audio play() succeeded',data:{volume:audio.volume,muted:audio.muted,paused:audio.paused,readyState:audio.readyState},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
              // #endregion
              // Verify audio is actually playing
              setTimeout(() => {
                // #region agent log
                fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:355',message:'Audio playback check',data:{paused:audio.paused,ended:audio.ended,currentTime:audio.currentTime,duration:audio.duration,volume:audio.volume,muted:audio.muted},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
                // #endregion
                // If audio is paused or ended unexpectedly, try to resume
                if (audio.paused && !audio.ended && audio.readyState >= 2) {
                  console.warn('Audio paused unexpectedly, attempting to resume');
                  audio.play().catch(err => {
                    console.error('Failed to resume audio:', err);
                  });
                }
              }, 100);
            })
            .catch((playError) => {
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:352',message:'Audio play() failed',data:{error:playError.message,name:playError.name,volume:audio.volume,muted:audio.muted},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
              // #endregion
              console.error('Audio play() failed:', playError);
              // Notify user about autoplay policy
              if (playError.name === 'NotAllowedError') {
                this.notifySubscribers({
                  type: 'error',
                  message: 'Audio autoplay blocked. Please click anywhere on the page to enable audio playback.',
                  error: playError
                });
              }
              URL.revokeObjectURL(audioUrl);
              this.isPlaying = false;
              if (!resolved) {
                resolved = true;
                resolve(); // Resolve anyway so we don't block
              }
            });
        } else {
          // Fallback for older browsers
          if (!resolved) {
            resolved = true;
            resolve();
          }
        }
      });
      
      await playPromise;
      
      // Check if more chunks arrived while playing
      if (this.mp3Buffer && this.mp3Buffer.length > 0) {
        // More chunks arrived, play them
        this.playMP3Buffer();
      } else {
        this.isPlaying = false;
      }
    } catch (error) {
      console.error('Error playing MP3 audio:', error);
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/ee3ae33e-53ef-428c-9fc0-4351fd2ff4e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'socket.js:360',message:'Error in playMP3Buffer',data:{error:error.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
      // #endregion
      this.isPlaying = false;
      this.mp3Buffer = []; // Clear buffer on error
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
    if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected or not open, cannot send audio chunk. State:', this.ws?.readyState);
      return;
    }

    try {
      // Convert Float32Array to Int16Array if needed
      let audioData = chunk;
      
      if (chunk instanceof Float32Array) {
        // Convert float32 to int16 for transmission
        // Float32Array values are in [-1, 1] range
        // Int16Array values should be in [-32768, 32767] range
        const int16Array = new Int16Array(chunk.length);
        for (let i = 0; i < chunk.length; i++) {
          // Clamp to [-1, 1] and convert to int16
          const s = Math.max(-1, Math.min(1, chunk[i]));
          // Multiply by 32768 and clamp to int16 range
          int16Array[i] = Math.max(-32768, Math.min(32767, Math.round(s * 32768)));
        }
        audioData = int16Array.buffer;
      } else if (chunk instanceof ArrayBuffer) {
        audioData = chunk;
      } else if (chunk instanceof Blob) {
        audioData = chunk;
      } else {
        console.error('Unsupported audio chunk type:', typeof chunk, chunk);
        return;
      }

      // Send binary data
      if (audioData.byteLength > 0) {
        console.log('Sending audio data to WebSocket, size:', audioData.byteLength, 'bytes');
        this.ws.send(audioData);
      } else {
        console.warn('Audio data is empty, skipping send');
      }
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
    this.mp3Buffer = [];
    this.isPlaying = false;
    
    if (this.mp3PlayTimeout) {
      clearTimeout(this.mp3PlayTimeout);
      this.mp3PlayTimeout = null;
    }
    
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

