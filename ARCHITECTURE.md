# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend Layer (Browser)                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  React Application                         │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │           SignBridge Interface (Hearer/Deaf Mode)    │ │ │
│  │  ├──────────────────────────────────────────────────────┤ │ │
│  │  │ • Audio Capture (Microphone)                         │ │ │
│  │  │ • Video Input (Camera)                               │ │ │
│  │  │ • Avatar Rendering (Three.js)                        │ │ │
│  │  │ • Real-time Transcript Display                       │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │      Transport & State Management                    │ │ │
│  │  ├──────────────────────────────────────────────────────┤ │ │
│  │  │ • WebSocket Client (Real-time Bidirectional)        │ │ │
│  │  │ • HTTP Client (REST API)                            │ │ │
│  │  │ • Custom Hooks (State Management)                   │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  WebRTC ────► Audio/Video Capture                              │
│  Browser APIs ──► Microphone/Camera Access                      │
└──────────────────────────────────────────────────────────────────┘
                              │
                    WebSocket + HTTP
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Backend Layer (Cloud Run)                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  FastAPI Application                      │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │             API Routes & WebSocket Handler           │ │ │
│  │  │  • /health (Health Check)                            │ │ │
│  │  │  • /ws (WebSocket Endpoint)                          │ │ │
│  │  │  • /api/* (REST Endpoints)                           │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │       SignConversationAgent (ADK-Based)             │ │ │
│  │  │  • Tool: Speech-to-Text                             │ │ │
│  │  │  • Tool: Gemini Live API                            │ │ │
│  │  │  • Tool: Text-to-Speech                             │ │ │
│  │  │  • Tool: Sign Animation Generation                  │ │ │
│  │  │  • Tool: Session Management                         │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │           Service Layer                             │ │ │
│  │  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │  │ GeminiLiveService                              │ │ │
│  │  │  │ • Real-time Gemini API streaming               │ │ │
│  │  │  │ • Context & conversation management            │ │ │
│  │  │  └────────────────────────────────────────────────┘ │ │
│  │  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │  │ SpeechToTextService                            │ │ │
│  │  │  │ • Google Cloud Speech-to-Text                  │ │ │
│  │  │  │ • Streaming transcription                      │ │ │
│  │  │  └────────────────────────────────────────────────┘ │ │
│  │  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │  │ TextToSpeechService                            │ │ │
│  │  │  │ • Google Cloud Text-to-Speech                  │ │ │
│  │  │  │ • Audio generation & playback prep             │ │ │
│  │  │  └────────────────────────────────────────────────┘ │ │
│  │  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │  │ SignAnimationService                           │ │ │
│  │  │  │ • Avatar animation generation                  │ │ │
│  │  │  │ • Cloud Storage asset serving                  │ │ │
│  │  │  └────────────────────────────────────────────────┘ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │       Streaming & Session Management               │ │ │
│  │  │  • AudioStreamHandler                              │ │ │
│  │  │  • VideoStreamHandler                              │ │ │
│  │  │  • SessionManager                                  │ │ │
│  │  │  • ConversationMemory                              │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────────┐  ┌──────────────────┐  ┌──────────────┐
   │Vertex AI    │  │ Cloud Speech-to- │  │ Cloud Text-  │
   │Gemini Live  │  │ Text & Synthesis │  │to-Speech     │
   │   API       │  │                  │  │              │
   └─────────────┘  └──────────────────┘  └──────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │Cloud Storage │  │Redis/Memstore│  │Cloud Logging │
   │(Animations)  │  │(Sessions)    │  │& Monitoring  │
   └──────────────┘  └──────────────┘  └──────────────┘
```

## Component Breakdown

### Frontend Architecture

**React Components:**
- `SignBridgeInterface` - Main UI component with hearer/deaf mode toggle
- `AvatarRenderer` - Three.js based 3D avatar display
- `Controls` - Audio/video capture controls
- `Transcript` - Real-time transcript display
- `StatusIndicator` - Connection status display

**Custom Hooks:**
- `useWebSocket` - WebSocket connection management
- `useAudioCapture` - Microphone capture & recording
- `useAudioPlayback` - Audio playback & context management
- `useAvatarRenderer` - Three.js scene initialization
- `useConversationState` - Conversation state management

**Services:**
- `api.ts` - REST API client for backend communication
- WebSocket client (in `useWebSocket`)

**Key Dependencies:**
- React 18
- Three.js (3D graphics)
- Vite (build tool)
- TypeScript

### Backend Architecture

**API Layer (FastAPI):**
- `/health` - Health check endpoint
- `/ws` - WebSocket endpoint for bidirectional streaming
- REST endpoints for specific operations

**Agent Layer (Agent Development Kit):**
- `SignConversationAgent` - Main orchestration agent
- Tool execution and response routing

**Service Layer:**
- `GeminiLiveService` - Vertex AI integration
- `SpeechToTextService` - Google Cloud STT
- `TextToSpeechService` - Google Cloud TTS
- `SignAnimationService` - Avatar animation

**Streaming Layer:**
- `AudioStreamHandler` - Audio streaming management
- `VideoStreamHandler` - Video streaming management
- WebSocket protocol handlers

**Session Management:**
- `SessionManager` - Session lifecycle
- `ConversationMemory` - Context preservation
- Redis integration for distributed sessions

**Key Dependencies:**
- FastAPI
- Google Cloud SDKs (Vertex AI, Speech, Text-to-Speech)
- Pydantic (data validation)
- Redis (session storage)

## Data Flow

### Hearer → Deaf User Flow

```
1. Hearer speaks → Browser captures audio via WebRTC
                   ↓
2. Audio sent via WebSocket to backend
                   ↓
3. Backend receives audio chunk
                   ↓
4. SpeechToTextService transcribes audio
                   ↓
5. GeminiLiveService processes transcript with context
                   ↓
6. Gemini returns sign language description
                   ↓
7. SignAnimationService generates animation
                   ↓
8. Backend streams animation & text back via WebSocket
                   ↓
9. Frontend renders 3D avatar with animation
10. Text displayed to deaf user
```

### Deaf → Hearer User Flow

```
1. Deaf user signs → Browser captures video
                     ↓
2. Video sent to backend
                     ↓
3. Backend analyzes video (future: pose estimation)
                     ↓
4. GeminiLiveService interprets sign language
                     ↓
5. Gemini returns spoken language response
                     ↓
6. TextToSpeechService generates audio
                     ↓
7. Backend streams audio back
                     ↓
8. Frontend plays audio for hearer user
9. Text displayed for reference
```

## Deployment Architecture

### Local Development
```
Docker Compose
├── Frontend (Port 5173)
│   ├── Vite Dev Server
│   └── Hot Module Reloading
├── Backend (Port 8000)
│   ├── Uvicorn + FastAPI
│   └── Auto-reload
└── Redis (Port 6379)
    └── Session Store
```

### Cloud Deployment
```
Google Cloud
├── Cloud Run (Backend)
│   ├── Auto-scaling
│   ├── Managed deployment
│   └── HTTPS by default
├── Cloud Storage (Frontend + Assets)
│   ├── Static site hosting
│   └── Cloud CDN caching
├── Vertex AI (Model)
│   └── Gemini Live API
├── Cloud Speech-to-Text
│   └── Streaming API
├── Cloud Text-to-Speech
│   └── Streaming API
└── Memorystore Redis
    └── Session persistence
```

## Scalability Considerations

### Horizontal Scaling
- **Backend**: Cloud Run auto-scales based on CPU/request count
- **Frontend**: Served from Cloud Storage + CDN (static)
- **Redis**: Use Cloud Memorystore for auto-failover

### Vertical Scaling
- Increase Cloud Run memory (up to 8GB)
- Scale Vertex AI quota as needed
- Monitor CPU usage and adjust accordingly

### Rate Limiting
- Implement token bucket algorithm
- Limit concurrent WebSocket connections
- Queue long-running jobs

## Security Architecture

### Authentication & Authorization
- API key for service-to-service auth
- JWT tokens for user sessions (future)
- HTTPS/WSS encryption in transit

### Data Protection
- Encrypt secrets using Cloud Secret Manager
- Network isolation via VPC connectors
- Audit logging in Cloud Logging

### CORS & Policies
- Strict CORS configuration
- Cloud Armor for DDoS protection
- Binary Authorization for container images

## Monitoring & Observability

### Logging
- Structured logging with formatters
- Cloud Logging for centralized logs
- Error tracking with Cloud Error Reporting

### Metrics
- Request latency tracking
- WebSocket connection metrics
- Service health checks

### Tracing
- Distributed tracing with Cloud Trace
- Performance profiling
- Bottleneck identification

## Performance Optimization

### Frontend
- Code splitting with React.lazy
- Image optimization
- Browser caching with service workers (future)
- Lazy loading components

### Backend
- Connection pooling for APIs
- Request batching where possible
- Caching with Redis
- Efficient streaming protocols

### Network
- CloudCDN for static assets
- WebSocket for real-time (vs polling)
- Compression for payloads
- Connection reuse

---

## Technology Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Frontend Framework | React | Popular, component-based, good ecosystem |
| Build Tool | Vite | Fast HMR, optimized builds, modern tooling |
| 3D Graphics | Three.js | Industry standard, WebGL support, avatar rendering |
| Backend Framework | FastAPI | Async support, automatic docs, type hints |
| Database | Redis | Session caching, low latency |
| Real-time | WebSocket | Low latency, bidirectional, native browser support |
| AI Model | Gemini Live | Latest model, real-time streaming, multimodal |
| Deployment | Cloud Run | Serverless, auto-scaling, Google Cloud integration |
| Container | Docker | Consistent environments, easy deployment |

---

See [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment architecture details.
