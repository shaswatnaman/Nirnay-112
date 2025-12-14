# Nirnay AI: India-Context-Aware Emergency Response System

> **An AI-powered emergency response system designed specifically for the Indian context, handling Hindi/Hinglish speech, fragmented communication, and real-time incident extraction.**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Table of Contents

- [Problem Statement](#-problem-statement)
- [Solution Overview](#-solution-overview)
- [Indian Context Challenges](#-indian-context-challenges)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Setup Instructions](#-setup-instructions)
- [Usage](#-usage)
- [Features](#-features)
- [Limitations](#-limitations)
- [Future Improvements](#-future-improvements)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Problem Statement

### The Challenge: Chaotic Indian Emergency Calls

Emergency response systems in India face unique challenges that traditional systems fail to address:

- **Language Barriers**: Most callers speak Hindi or regional languages (Punjabi, Marathi, Tamil, Telugu, etc.), not English
- **Low Literacy Levels**: Callers often use incomplete sentences, vague descriptions, and unstructured speech
- **Emotional & Panic Communication**: In emergencies, people speak quickly, slur words, or become emotional
- **Incomplete Information**: Callers may not know exact addresses, street names, or incident types
- **High Call Volume**: Busy cities experience simultaneous emergency calls requiring scalable systems
- **Background Noise**: Street noise, vehicle sounds, and crowd chatter interfere with audio quality
- **Real-time Requirements**: Dispatchers need incident information as it's being collected, not at the end

Traditional emergency systems designed for English-speaking, structured communication fail in this context, leading to:
- Delayed response times
- Misrouted incidents
- Incomplete information collection
- Frustrated callers and dispatchers

---

## 💡 Solution Overview

**Nirnay AI** is an AI-powered emergency response system that:

1. **Handles Hindi/Hinglish Speech**: Uses Whisper STT trained for Hindi and code-switching
2. **Real-time Questioning**: Dynamically generates contextual Hindi questions based on missing information
3. **Progressive Incident Extraction**: Builds incident reports incrementally from fragmented speech
4. **Live Updates**: Provides real-time transcripts and incident information to dispatchers
5. **Intelligent Escalation**: Detects when human intervention is needed (panic, high urgency, missing critical fields)
6. **Scalable Architecture**: Handles multiple simultaneous calls with session-based state management

### Key Capabilities

- ✅ **Hindi/Hinglish Speech Recognition**: Real-time transcription of mixed-language speech
- ✅ **Fragmented Speech Handling**: Extracts meaning from incomplete sentences
- ✅ **Emotional Speech Processing**: Handles panic, fast speech, and emotional cues
- ✅ **Dynamic Question Generation**: Context-aware Hindi questions based on missing fields
- ✅ **Live Incident Building**: Progressive extraction of name, location, incident type, urgency
- ✅ **Human Escalation**: Automatic detection of situations requiring human operators
- ✅ **Real-time Updates**: Live transcripts and incident panel for dispatchers

---

## 🇮🇳 Indian Context Challenges

Nirnay AI is specifically designed to handle the unique challenges of the Indian emergency response context:

### 1️⃣ Language & Literacy Challenges

| Challenge | Indian Context | Solution in Nirnay AI |
|-----------|---------------|----------------------|
| **Regional Languages & Hindi Preference** | Most users speak Hindi or regional languages (Punjabi, Marathi, Tamil, etc.). English-only systems fail here. | Whisper STT model tuned for Hindi, with Hinglish code-switching support. NLP modules handle Hindi-first input with regional language expansion capability. |
| **Low Literacy / Unstructured Speech** | Users often speak incomplete sentences: *"Mere ghar ke samne… kuchh hua"* instead of full structured sentences. | NLP modules (`intent.py`, `entities.py`) handle fragmented sentences. Entity extraction works with partial information. Conversation manager asks clarifying questions. |
| **Hinglish and Transliteration** | Many people speak in Romanized Hindi or mixed languages: *"Fire ho gaya yahan par"*. | Whisper + NLP trained/tuned to handle mixed language input. Keyword dictionaries include both Hindi and English variations. |

### 2️⃣ Audio & Speech Challenges

| Challenge | Indian Context | Solution in Nirnay AI |
|-----------|---------------|----------------------|
| **Fast, Slurred, or Emotional Speech** | In emergencies, people speak quickly, sometimes panicked. Words can be mispronounced or incomplete. | Chunked audio streaming (500ms chunks). Partial transcription support. Confidence-based entity extraction. Audio enhancement in `whisper_stt.py`. |
| **Background Noise** | Streets, vehicles, or crowd noise is common in Indian calls. | Whisper model handles noise. Chunking + repeated transcription helps. Audio preprocessing filters low-frequency noise. |
| **Interruptions & Overlapping Speech** | Users may interrupt AI questions or start new sentences. | Backend tracks partial transcripts. Conversation manager maintains dialogue context. Order context engine accumulates information across chunks. |

### 3️⃣ Content & Communication Challenges

| Challenge | Indian Context | Solution in Nirnay AI |
|-----------|---------------|----------------------|
| **Vague Descriptions** | People often say *"kuch ho gaya"* without specifying accident, crime, or fire. | Intent detection (`intent.py`) classifies from vague input. Conversation manager generates clarifying questions dynamically. |
| **Emotional Cues** | Panic, crying, anger, stress can indicate urgency, even if words are unclear. | Escalation module (`escalation.py`) uses emotional keywords. Panic indicators trigger human escalation. Urgency detection from emotional markers. |
| **Incomplete Location Info** | People may say *"Gali ke end me"* without city or landmark. | Iterative AI questioning. Location extraction handles partial addresses. Conversation manager prioritizes location questions. |
| **Repeated or Irrelevant Calls** | Some calls may be non-emergent. | Intent detection classifies non-urgent requests. Low urgency handling. Optional confirmation questions. |

### 4️⃣ Interaction & Usability Challenges

| Challenge | Indian Context | Solution in Nirnay AI |
|-----------|---------------|----------------------|
| **Live Conversation Expectation** | People expect human-like interaction, not robotic prompts. | AI questions generated in natural Hindi. Context-aware question generation. Respectful, formal tone. |
| **Real-time Updates Required** | Dispatchers want incident info as it's being collected, not at the end. | Live transcript updates via WebSocket. Incident panel updates in real-time. Progressive field filling. |
| **Handling Panic / Language Barrier** | AI may need to repeat questions, slow down speech, or simplify language. | Escalation module detects panic. Human intervention flag. TTS can adjust speed. Simple vocabulary for low literacy. |
| **Limited User Input / Illiterate Callers** | Users may not know addresses, street numbers, or exact incident type. | Handles approximate data. Optional fields. Escalation when critical fields missing. |

### 5️⃣ System-Level Challenges

| Challenge | Indian Context | Solution in Nirnay AI |
|-----------|---------------|----------------------|
| **Scalability** | Many simultaneous calls in busy cities. | Backend handles multiple WebSocket sessions. Session-based state management. Per-call order context tracking. |
| **Reliability** | Calls may drop, audio may be distorted. | Partial transcription. Retry logic. Incremental updates. WebSocket reconnection. |
| **Ethical / Safety Concerns** | AI decisions must always allow human override. | Escalation logic is critical. `human_required` flag. Manual escalation support. Safety-first design. |

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ LiveTranscript│  │ IncidentPanel│  │ ControlPanel │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                  │
│                    WebSocket Client                           │
│                    (socket.js)                                │
└────────────────────────────┼─────────────────────────────────┘
                             │
                    WebSocket /ws/call
                             │
┌────────────────────────────┼─────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           WebSocket Handler (websocket.py)           │  │
│  │  - Session Management                                │  │
│  │  - Audio Chunk Processing                            │  │
│  │  - Real-time Updates                                │  │
│  └───────┬──────────────────────┬──────────────────────┘  │
│          │                      │                          │
│  ┌───────▼────────┐    ┌────────▼──────────┐            │
│  │ Whisper STT    │    │ Conversation       │            │
│  │ (whisper_stt)  │───▶│ Manager            │            │
│  │                │    │ (conversation.py)  │            │
│  └────────────────┘    └───────┬───────────┘            │
│                                 │                          │
│                    ┌────────────┼────────────┐            │
│                    │            │            │            │
│          ┌─────────▼──┐  ┌──────▼─────┐  ┌─▼──────────┐ │
│          │ Intent     │  │ Entities   │  │ Order      │ │
│          │ Detection  │  │ Extraction │  │ Context    │ │
│          │ (intent.py)│  │(entities.py)│  │(order_ctx) │ │
│          └────────────┘  └────────────┘  └────────────┘ │
│                                                           │
│          ┌──────────────┐  ┌──────────────┐             │
│          │ Escalation   │  │ TTS          │             │
│          │ (escalation)  │  │ (tts.py)     │             │
│          └──────────────┘  └──────────────┘             │
└───────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### **Backend Architecture**

1. **WebSocket Handler** (`websocket.py`)
   - Manages multiple simultaneous sessions
   - Receives binary audio chunks
   - Processes transcripts and sends updates
   - Handles disconnects and errors

2. **Speech Processing**
   - **Whisper STT** (`whisper_stt.py`): Hindi/Hinglish transcription with noise handling
   - **TTS** (`tts.py`): Hindi text-to-speech with chunked streaming

3. **NLP Pipeline**
   - **Intent Detection** (`intent.py`): Classifies incident type (Accident, Crime, Medical, Non-Urgent)
   - **Entity Extraction** (`entities.py`): Extracts name, location, incident_type, urgency
   - **Order Context** (`order_context.py`): Maintains per-session state, progressive field updates

4. **Conversation Management**
   - **ConversationManager** (`conversation.py`): Orchestrates conversation flow, generates Hindi questions
   - **Escalation** (`escalation.py`): Detects when human intervention is needed

5. **Data Models** (`schemas.py`)
   - Pydantic models for type safety and validation

#### **Frontend Architecture**

1. **WebSocket Service** (`socket.js`)
   - Manages WebSocket connection
   - Handles audio streaming
   - Subscribes to real-time updates

2. **Components**
   - **LiveTranscript**: Real-time conversation display
   - **IncidentPanel**: Incident information with color-coded urgency
   - **ControlPanel**: Call control actions
   - **App**: Main orchestrator with microphone streaming

---

## 🛠️ Tech Stack

### Backend

- **Python 3.9+**
- **FastAPI**: Modern, fast web framework for APIs and WebSockets
- **Whisper (OpenAI)**: Speech-to-text model (small variant for Hindi)
- **gTTS**: Google Text-to-Speech for Hindi TTS
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server for FastAPI
- **NumPy**: Audio processing
- **PyTorch**: Required for Whisper model

### Frontend

- **React 18+**: UI library
- **WebSocket API**: Real-time communication
- **Web Audio API**: Microphone capture and audio playback
- **CSS3**: Styling and responsive design

### Infrastructure

- **WebSocket**: Real-time bidirectional communication
- **REST API**: Health checks and status endpoints

---

## 🚀 Setup Instructions

### Prerequisites

- Python 3.9 or higher
- Node.js 16+ and npm
- Microphone access (for testing)
- 4GB+ RAM (for Whisper model)

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Nirnay-112
   ```

2. **Navigate to backend directory**
   ```bash
   cd backend
   ```

3. **Create virtual environment** (recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Download Whisper model** (automatic on first use)
   - The model will be downloaded automatically when first used
   - Ensure stable internet connection for first run

6. **Start the server**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

   The API will be available at:
   - API: `http://localhost:8000`
   - WebSocket: `ws://localhost:8000/ws/call`
   - Health Check: `http://localhost:8000/health`
   - API Docs: `http://localhost:8000/docs`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend/src
   ```

2. **Install dependencies** (if using npm)
   ```bash
   npm install
   ```

3. **Start development server** (if using Vite/React)
   ```bash
   npm run dev
   ```

   Or serve the files using a static server:
   ```bash
   # Using Python
   python3 -m http.server 5173
   
   # Using Node.js
   npx serve -p 5173
   ```

4. **Open in browser**
   - Navigate to `http://localhost:5173`
   - Allow microphone access when prompted

### Environment Configuration

Create a `.env` file in the backend directory (optional):

```env
# Backend Configuration
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:5173

# Whisper Configuration
WHISPER_MODEL=small
WHISPER_LANGUAGE=hi

# TTS Configuration
TTS_LANGUAGE=hi
```

---

## 📖 Usage

### Live Call Demo

1. **Start Backend**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Start Frontend**
   ```bash
   cd frontend/src
   # Serve files on port 5173
   ```

3. **Open Application**
   - Navigate to `http://localhost:5173`
   - Click "Start Recording" button
   - Allow microphone access

4. **Make a Test Call**
   - Speak in Hindi/Hinglish: *"मेरा नाम राम है, दिल्ली में दुर्घटना हुई, तुरंत मदद चाहिए"*
   - Watch real-time transcript updates
   - See incident panel fill progressively
   - Listen to AI responses in Hindi

5. **Monitor Incident Information**
   - **Live Transcript**: See user and AI speech in real-time
   - **Incident Panel**: Watch fields update as information is extracted
   - **Control Panel**: Use buttons to escalate, end call, or mark resolved

### Example Conversation Flow

```
User: "नमस्ते, मेरा नाम राम है"
AI: "नमस्ते राम, मैं आपकी मदद के लिए यहाँ हूँ। कृपया बताएं कि क्या हुआ है?"

User: "दिल्ली में दुर्घटना हुई"
AI: "कृपया बताएं कि यह घटना कहाँ हुई है?"

User: "कनॉट प्लेस के पास"
AI: "यह कितना जरूरी है? क्या यह तत्काल मदद की आवश्यकता है?"

User: "हाँ, तुरंत मदद चाहिए"
AI: "मैं समझ गया। आपकी मदद के लिए एक व्यक्ति जल्द ही आपसे बात करेगा।"
```

### API Endpoints

- **GET `/health`**: Health check endpoint
  ```bash
  curl http://localhost:8000/health
  ```

- **WebSocket `/ws/call`**: Real-time call endpoint
  - Connect with session initialization
  - Send binary audio chunks
  - Receive transcripts, incident updates, and AI audio

---

## ✨ Features

### Core Features

- ✅ **Real-time Hindi/Hinglish Speech Recognition**
- ✅ **Progressive Incident Extraction** (name, location, type, urgency)
- ✅ **Dynamic Hindi Question Generation**
- ✅ **Live Transcript Updates**
- ✅ **Real-time Incident Panel**
- ✅ **Intelligent Escalation Detection**
- ✅ **Multiple Simultaneous Sessions**
- ✅ **Audio Streaming & Playback**

### Indian Context Features

- ✅ **Fragmented Speech Handling**
- ✅ **Emotional Speech Processing**
- ✅ **Background Noise Reduction**
- ✅ **Low Literacy Adaptation**
- ✅ **Vague Description Handling**
- ✅ **Incomplete Location Extraction**
- ✅ **Panic Detection & Escalation**

---

## ⚠️ Limitations

### Current Limitations

1. **Language Support**
   - Primary support for Hindi/Hinglish
   - Regional languages (Punjabi, Marathi, Tamil) require additional training
   - English support is limited

2. **Model Performance**
   - Whisper "small" model used (balance of speed/accuracy)
   - Larger models (medium, large) provide better accuracy but slower
   - Real-time processing may have slight delays

3. **Audio Quality**
   - Requires reasonable audio quality for best results
   - Very noisy environments may reduce accuracy
   - Network latency affects real-time experience

4. **Scalability**
   - In-memory session storage (not suitable for production scale)
   - No database persistence
   - Single server deployment

5. **Error Handling**
   - Limited retry logic for failed transcriptions
   - No fallback mechanisms for model failures
   - WebSocket reconnection may drop session state

6. **Security**
   - No authentication/authorization
   - No encryption for sensitive data
   - No rate limiting

### Known Issues

- Audio chunk timing may cause slight delays
- Very fast speech may miss some words
- Background noise can interfere with transcription
- Long conversations may accumulate memory

---

## 🔮 Future Improvements

### Short-term (1-3 months)

1. **Enhanced Language Support**
   - Add regional language models (Punjabi, Marathi, Tamil, Telugu)
   - Improve Hinglish code-switching detection
   - Support for more regional dialects

2. **Model Optimization**
   - Upgrade to Whisper "medium" or "large" for better accuracy
   - Fine-tune models on Indian emergency call datasets
   - Implement model caching and optimization

3. **Database Integration**
   - Add PostgreSQL/MongoDB for session persistence
   - Store incident history and analytics
   - Enable multi-server deployment

4. **Improved Error Handling**
   - Robust retry mechanisms
   - Fallback transcription services
   - Better WebSocket reconnection with state recovery

### Medium-term (3-6 months)

5. **Advanced NLP**
   - Fine-tuned LLM for question generation
   - Better entity extraction with NER models
   - Sentiment analysis for emotional detection

6. **Scalability**
   - Redis for distributed session management
   - Load balancing for multiple servers
   - Horizontal scaling support

7. **Security & Compliance**
   - Authentication and authorization
   - End-to-end encryption
   - GDPR/Data protection compliance
   - Audit logging

8. **Analytics & Monitoring**
   - Real-time metrics dashboard
   - Call quality monitoring
   - Incident analytics
   - Performance tracking

### Long-term (6-12 months)

9. **Multi-modal Support**
   - Image/video incident reporting
   - Location sharing via GPS
   - Live video streaming

10. **AI Improvements**
    - Fine-tuned models on Indian emergency data
    - Transfer learning for regional languages
    - Active learning from human feedback

11. **Integration**
    - Integration with emergency services (police, fire, medical)
    - SMS/WhatsApp fallback channels
    - Mobile app development

12. **Advanced Features**
    - Predictive incident routing
    - Resource allocation optimization
    - Historical pattern analysis
    - Automated dispatch recommendations

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use ESLint for JavaScript/React code
- Write comprehensive comments
- Add tests for new features
- Update documentation

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OpenAI Whisper** for speech recognition
- **FastAPI** for the excellent web framework
- **React** team for the UI library
- **gTTS** for text-to-speech functionality

---

## 📧 Contact

For questions, issues, or contributions, please open an issue on GitHub.

---

**Built with ❤️ for India's emergency response needs**

