# BUILD & RUN GUIDE for SignBridge Live

## Quick Start (5 minutes)

### Option 1: Using Docker Compose (Recommended)

```bash
# Navigate to backend directory
cd signbridge-backend

# Start entire stack (backend, frontend, redis)
docker-compose up --build

# Wait for services to start, then open:
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# Backend Docs: http://localhost:8000/docs
```

### Option 2: Manual Setup

#### Backend
```bash
cd signbridge-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend (in a new terminal)
```bash
cd signbridge-frontend
npm install
npm run dev
```

Then open http://localhost:5173

---

## Detailed Build Steps

### Prerequisites

- **Node.js**: 16 or higher (check: `node --version`)
- **Python**: 3.11 or higher (check: `python --version`)
- **npm/yarn**: Latest version
- **Docker** (optional): For containerized setup

### Backend Build

#### Step 1: Set Up Python Environment

```bash
cd signbridge-backend

# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Step 2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 3: Configure Environment

Create `.env` file in `signbridge-backend/`:

```env
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_REGION=us-central1
VERTEX_AI_MODEL=gemini-2.0-flash

# Server Configuration
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000

# Session Management
REDIS_URL=redis://localhost:6379
SESSION_TIMEOUT=3600

# Logging
LOG_LEVEL=INFO
```

#### Step 4: Run Backend

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

Verify it works: `curl http://localhost:8000/health`

### Frontend Build

#### Step 1: Install Dependencies

```bash
cd signbridge-frontend
npm install
```

#### Step 2: Configure Environment

Create `.env` file in `signbridge-frontend/`:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

#### Step 3: Run Development Server

```bash
npm run dev
```

Expected output:
```
VITE v4.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  press h to show help
```

Open http://localhost:5173 in your browser.

### Production Build

#### Backend Docker Build

```bash
cd signbridge-backend

# Build image
docker build -f docker/Dockerfile -t signbridge-backend:1.0.0 .

# Run container
docker run -p 8000:8000 \
  -e GOOGLE_CLOUD_PROJECT=your-project \
  -e GOOGLE_CLOUD_REGION=us-central1 \
  signbridge-backend:1.0.0
```

#### Frontend Production Build

```bash
cd signbridge-frontend

# Create optimized build
npm run build

# Output directory: dist/
# Files are minified, tree-shaken, and optimized

# Preview locally
npm run preview
```

---

## Running Tests

### Backend Tests

```bash
cd signbridge-backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_api.py::test_health_check -v
```

### Frontend Tests

```bash
cd signbridge-frontend

# Run tests (if configured)
npm test

# Run with coverage
npm test -- --coverage
```

---

## Troubleshooting

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :8000
kill -9 <PID>
```

### Python Virtual Environment Issues

```bash
# Verify venv is activated (should show (venv) in prompt)
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Node Modules Issues

```bash
# Clear npm cache
npm cache clean --force

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### WebSocket Connection Failed

1. Check backend is running: `curl http://localhost:8000/health`
2. Verify VITE_WS_URL in .env points to correct backend
3. Check browser console for error messages
4. Ensure port 8000 is not blocked by firewall

### Docker Issues

```bash
# View logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild everything
docker-compose down -v
docker-compose up --build

# Remove containers
docker-compose down

# Clean up resources
docker system prune -a
```

---

## File Structure After Build

### Backend Build Artifacts
```
signbridge-backend/
├── venv/                    # Python virtual environment
├── __pycache__/            # Python cache
├── app/                    # Source code
└── requirements.txt        # Dependencies
```

### Frontend Build Artifacts
```
signbridge-frontend/
├── node_modules/           # npm dependencies
├── dist/                   # Production build (created by npm run build)
├── src/                    # Source code
├── package.json            # npm configuration
└── vite.config.ts          # Vite configuration
```

---

## Development vs Production

| Aspect | Development | Production |
|---|---|---|
| Auto-reload | ✅ Yes | ❌ No |
| Source maps | ✅ Yes | ❌ No |
| Code minification | ❌ No | ✅ Yes |
| Performance | Lower | Higher |
| Bundle size | Larger | Smaller |
| Error messages | Verbose | User-friendly |

---

## Useful Commands

### Backend

```bash
# Format code
black app/

# Lint code
flake8 app/

# Type check
mypy app/

# Run specific service
python -c "from app.services.gemini_live_service import GeminiLiveService; print('Service OK')"
```

### Frontend

```bash
# Format code
npm run format

# Lint code
npm run lint

# Type check
npx tsc --noEmit

# Build with stats
npm run build -- --stats
```

---

## Next Steps

1. ✅ Backend running at http://localhost:8000
2. ✅ Frontend running at http://localhost:5173
3. 📖 Read [project-details.MD](./project-details.MD) for architecture
4. 📖 Read [DEPLOYMENT.md](./DEPLOYMENT.md) for production setup
5. 🧪 Run tests: `npm test` (frontend), `pytest` (backend)
6. 🚀 Deploy to Google Cloud (see DEPLOYMENT.md)

---

## Support & Documentation

- **Backend API Docs**: http://localhost:8000/docs
- **Vite Docs**: https://vitejs.dev/
- **React Docs**: https://react.dev/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Google Vertex AI**: https://cloud.google.com/vertex-ai

