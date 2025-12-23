# Nirnay-112 - Diagnostic Steps

## Quick Diagnostic Checklist

### 1. Check Backend is Running
```bash
curl http://localhost:8000/health
```
Should return: `{"status":"ok"}`

### 2. Check Backend Logs
```bash
tail -f /tmp/nirnay-backend.log
```

### 3. Check Browser Console
Open browser DevTools (F12) and check:
- WebSocket connection status
- Audio processor logs
- Any errors

### 4. Test WebSocket Connection
In browser console, run:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/call');
ws.onopen = () => console.log('✅ WebSocket connected');
ws.onerror = (e) => console.error('❌ WebSocket error:', e);
ws.onmessage = (e) => console.log('📨 Message:', e.data);
ws.send(JSON.stringify({type: 'session_init', session_id: 'test'}));
```

### 5. Test Audio Capture
In browser console (after clicking Start Recording):
```javascript
// Check if microphone is active
navigator.mediaDevices.getUserMedia({audio: true})
  .then(stream => {
    console.log('✅ Microphone access granted');
    console.log('Tracks:', stream.getTracks());
    console.log('Active:', stream.active);
  })
  .catch(err => console.error('❌ Microphone error:', err));
```

## Common Issues

1. **No audio chunks received**: Check if ScriptProcessorNode is working
2. **WebSocket disconnects**: Check backend logs for errors
3. **No transcription**: Check if Whisper model is loaded
4. **No AI response**: Check if TTS is working

