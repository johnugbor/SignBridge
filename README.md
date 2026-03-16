# SignBridge Live

A real-time web application that enables bidirectional communication between deaf and hearing users using Google's Gemini Live API.

## Project Overview

SignBridge Live translates communication in real-time:
- **Deaf users** sign via camera → app interprets and speaks natural audio

- **Hearing users** speak → app translates to text


### Tech Stack

**Backend:**
- Python 3.11+
- FastAPI
- Google Vertex AI (Gemini Live API)
- WebSocket for real-time streaming
- Cloud Speech-to-Text & Cloud Text-to-Speech

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- Three.js (3D avatar rendering)
- WebSocket client

**Deployment:**
- Docker & Docker Compose
- Google Cloud Run

## Project Structure

```
SignB/
├── signbridge-backend/          # FastAPI Backend
│   ├── app/
│   │   ├── api/                # API endpoints
│   │   ├── services/           # Service layer (Gemini, TTS, STT)
│   │   ├── agents/             # Agent Development Kit agents
│   │   ├── models/             # Pydantic models
│   │   ├── session/            # Session & conversation management
│   │   └── streaming/          # Audio/video stream handlers
│   ├── docker/                 # Docker configuration
│   ├── requirements.txt        # Python dependencies
│   ├── docker-compose.yml      # Local development setup
│   └── README.md
│
├── signbridge-frontend/         # React Frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── services/           # API & WebSocket clients
│   │   ├── types/              # TypeScript definitions
│   │   └── pages/              # Page components
│   ├── index.html              # Entry HTML
│   ├── vite.config.ts          # Vite configuration
│   ├── package.json
│   └── README.md
│
└── project-details.MD          # Full project specification
```

## Getting Started

### Prerequisites

- Node.js 16+ (for frontend)
- Python 3.11+ (for backend)
- Docker & Docker Compose (optional, for containerized setup)
- Google Cloud project with Vertex AI enabled

### Backend Setup

```bash
cd signbridge-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with Google Cloud credentials
echo "GCP_PROJECT_ID=your-project-id" > .env
echo "GCP_REGION=us-central1" >> .env
echo "GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json" >> .env

# Run development server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

Health check: `curl http://localhost:8000/api/health`

### Frontend Setup

```bash
cd signbridge-frontend

# Install dependencies
npm install

# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env
echo "VITE_WS_URL=ws://localhost:8000/ws/signbridge" >> .env

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Docker Setup (Backend + Redis)

```bash
cd signbridge-backend

# Build and start all services
docker-compose up --build

# Access the backend:
# Backend API: http://localhost:8000
# Backend Docs: http://localhost:8000/docs
```

## Reproducible Testing (For Judges)

Use these exact steps from a clean checkout to validate the project.

### 1) Start The Stack

```bash
cd signbridge-backend
docker-compose up --build
```

In a second terminal, start the frontend:

```bash
cd signbridge-frontend
npm install
npm run dev
```

Expected:
- Backend on `http://localhost:8000`
- Frontend on `http://localhost:5173`

### 2) Verify Backend Liveness And Readiness

Run these in a new terminal:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/readiness
```

Expected responses:

```json
{"status":"ok"}
{"status":"ready"}
```

### 3) Verify WebSocket Handshake

Open `http://localhost:5173`, then open browser DevTools Console and run:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/signbridge')
ws.onmessage = (event) => console.log(JSON.parse(event.data))
```

Expected first server message:
- `type: "session_ack"`
- `payload.session_id` present

### 4) Functional Smoke Test

In the UI:

1. Select `Hearer Mode`, hold mic button for 2-3 seconds, then release.
2. Confirm transcript updates in the UI.
3. Select `Deaf Mode`, start camera capture, sign briefly, then stop.
4. Confirm transcript/audio response is returned.

Pass criteria:
- No frontend crash
- WebSocket remains connected
- Transcript/response updates appear in real time

### 5) Optional: Run Backend Test Suite

```bash
cd signbridge-backend
pip install pytest pytest-cov pytest-asyncio httpx
pytest --maxfail=1 -q
```

Note:
- Frontend unit test scripts are not configured in `package.json` yet.
- Additional testing details are documented in `TESTING.md`.

## Development Workflow

### Making Changes

**Backend changes:**
1. Edit files in `signbridge-backend/app/`
2. The server auto-reloads with `--reload` flag
3. Check logs in the terminal

**Frontend changes:**
1. Edit files in `signbridge-frontend/src/`
2. Vite will hot-reload the browser
3. Check console for TypeScript errors

### Building for Production

**Backend:**
```bash
cd signbridge-backend
docker build -f docker/Dockerfile -t signbridge-backend:latest .
```

**Frontend:**
```bash
cd signbridge-frontend
npm run build
# Output is in `dist/` directory
```

## API Documentation

- **Backend Docs**: http://localhost:8000/docs (Swagger UI)
- **Backend ReDoc**: http://localhost:8000/redoc

## Key Features

### Real-time Communication
- WebSocket-based bidirectional streaming
- Low-latency audio/video processing
- Automatic reconnection with exponential backoff

### Multi-modal Processing
- Speech-to-Text: Convert voice to text
- Text-to-Speech: Convert text to natural speech
- Sign Animation: Render animated sign language avatar
- Camera Input: Capture and process user's sign language

### Advanced Avatar Rendering
- 3D avatar using Three.js
- Real-time animation synchronization
- Customizable avatar models

## Environment Variables

### Backend (.env)
```
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GEMINI_MODEL_NAME=gemini-1.5-flash
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
AVATAR_STORAGE_BUCKET=your-bucket-name
REDIS_URL=redis://localhost:6379  # Optional, for session persistence
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/signbridge
```

## Performance Targets

- **End-to-end latency**: < 1.5 seconds
- **Audio quality**: 16kHz mono PCM
- **Video quality**: 30 FPS @ 720p
- **Concurrent connections**: 100+ users

## Troubleshooting

### WebSocket Connection Fails
- Ensure backend is running: `curl http://localhost:8000/api/health`
- Check firewall settings (port 8000)
- Verify WebSocket proxy in Vite config

### Audio Not Working
- Check browser microphone permissions
- Ensure AudioContext is initialized (click anywhere)
- Check browser console for errors

### Google Cloud Issues
- Verify credentials: `gcloud auth application-default login`
- Check project ID matches in .env
- Ensure Vertex AI API is enabled

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Test thoroughly (especially real-time features)
4. Submit a pull request

## Deployment to Google Cloud

See [DEPLOYMENT.md](./DEPLOYMENT.md) for Google Cloud Run setup instructions.

## License

MIT

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review backend logs: `docker-compose logs backend`
3. Check browser console for frontend errors
4. Open an issue with reproduction steps

## Roadmap

- [ ] Multi-user sessions
- [ ] Recording and replay
- [ ] Custom avatar training
- [ ] Accessibility improvements
- [ ] Mobile app (React Native)
- [ ] Offline mode with sync
