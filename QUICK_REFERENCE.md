# Quick Reference Guide

## Common Commands

### Backend

```bash
# Development
cd signbridge-backend
source venv/bin/activate
python -m uvicorn app.main:app --reload

# Testing
pytest -v --cov=app

# Linting & Formatting
black app/
isort app/
flake8 app/
mypy app/

# Building Docker image
docker build -f docker/Dockerfile -t signbridge-backend:latest .
```

### Frontend

```bash
# Development
cd signbridge-frontend
npm install
npm run dev

# Testing
npm test

# Linting & Formatting
npm run lint
npm run format

# Building
npm run build
npm run preview

# Building Docker image
docker build -t signbridge-frontend:latest .
```

### Docker Compose (Full Stack)

```bash
cd signbridge-backend

# Start
docker-compose up --build

# Stop
docker-compose down

# View logs
docker-compose logs -f
```

## Environment Variables

### Backend (.env)
```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1
VERTEX_AI_MODEL=gemini-2.0-flash
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## Port Reference

| Service | Port | URL |
|---------|------|-----|
| Frontend (Dev) | 5173 | http://localhost:5173 |
| Frontend (Prod) | 5173 | http://localhost:5173 |
| Backend API | 8000 | http://localhost:8000 |
| Backend Docs | 8000 | http://localhost:8000/docs |
| Redis | 6379 | redis://localhost:6379 |

## File Locations

### Key Backend Files
- Entry point: `signbridge-backend/app/main.py`
- API routes: `signbridge-backend/app/api/`
- Services: `signbridge-backend/app/services/`
- WebSocket: `signbridge-backend/app/api/websocket.py`

### Key Frontend Files
- Root: `signbridge-frontend/src/App.tsx`
- Components: `signbridge-frontend/src/components/`
- Hooks: `signbridge-frontend/src/hooks/`
- Types: `signbridge-frontend/src/types/`

## API Endpoints

### Health & Status
- `GET /health` - Server health check
- `GET /docs` - Swagger documentation
- `GET /redoc` - ReDoc documentation

### WebSocket
- `WS /ws` - Real-time communication

### Messages (Planned)
- `POST /messages` - Send text message
- `POST /audio/transcribe` - Transcribe audio
- `POST /audio/synthesize` - Generate speech

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes and commit
git add .
git commit -m "feat: your feature"

# Push and create PR
git push origin feature/your-feature

# After review, merge to main
git checkout main
git pull origin main
git merge feature/your-feature
git push origin main
```

## Debugging

### Backend
- Logs: `docker-compose logs backend -f`
- API Docs: http://localhost:8000/docs
- Python debugger: `import pdb; pdb.set_trace()`

### Frontend
- Console: F12 or Cmd+Opt+I
- DevTools Network: Check WebSocket connections
- React DevTools: Inspect component state

## Performance Benchmarks

| Metric | Target | Acceptable |
|--------|--------|-----------|
| End-to-end latency | < 1.5s | < 2s |
| API response time | < 100ms | < 200ms |
| WebSocket message | < 50ms | < 100ms |
| Frontend load | < 2s | < 3s |

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill process using port
taskkill /PID <PID> /F
```

### WebSocket connection fails
- Verify backend is running
- Check CORS settings
- Verify firewall allows port 8000

### Frontend build fails
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Docker issues
```bash
# Remove all containers and images
docker system prune -a

# Rebuild
docker-compose build --no-cache
```

## Useful Links

- **Backend Docs**: http://localhost:8000/docs
- **Frontend Dev**: http://localhost:5173
- **Project Spec**: [project-details.MD](./project-details.MD)
- **Deployment**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Building**: [BUILD.md](./BUILD.md)
- **Testing**: [TESTING.md](./TESTING.md)
- **Contributing**: [CONTRIBUTING.md](./CONTRIBUTING.md)

## Documentation Quick Links

| Topic | File |
|-------|------|
| Project Overview | README.md |
| Building & Setup | BUILD.md |
| Testing | TESTING.md |
| Deployment | DEPLOYMENT.md |
| DevOps & Infrastructure | DEVOPS.md |
| Contributing | CONTRIBUTING.md |
| Project Specification | project-details.MD |

---

**Stuck? Check the Documentation!**

Each guide builds on the others. Start with README.md, then jump to the relevant guide.
