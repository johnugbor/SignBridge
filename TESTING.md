# Testing Guide

## Overview

SignBridge Live has a comprehensive testing strategy covering:
- Unit tests
- Integration tests
- End-to-end tests
- Performance tests

## Backend Testing

### Setup

```bash
cd signbridge-backend

# Install test dependencies
pip install pytest pytest-cov pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::test_health_check -v
```

### Test Structure

```
signbridge-backend/tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_api.py              # API endpoint tests
├── test_services.py         # Service layer tests
├── test_agents.py           # Agent tests
├── test_streaming.py        # Streaming tests
├── test_session.py          # Session management tests
└── test_models.py           # Model validation tests
```

### Writing Tests

#### API Endpoint Tests

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def authenticated_client():
    """Provide authenticated test client"""
    headers = {"Authorization": f"Bearer test-token"}
    return headers

def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection"""
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "connection"
```

#### Service Tests

```python
# tests/test_services.py
import pytest
from app.services.speech_to_text_service import SpeechToTextService
from unittest.mock import AsyncMock, patch

@pytest.fixture
async def speech_service():
    """Provide speech service instance"""
    return SpeechToTextService()

@pytest.mark.asyncio
async def test_transcribe(speech_service):
    """Test speech transcription"""
    with patch.object(speech_service, 'transcribe', new_callable=AsyncMock) as mock:
        mock.return_value = "Hello world"
        result = await speech_service.transcribe(audio_data=b"audio")
        assert result == "Hello world"
        mock.assert_called_once()
```

### Running Tests in CI/CD

```yaml
# .github/workflows/test.yml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests
        run: |
          pytest --cov=app --cov-report=xml --cov-report=html
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Frontend Testing

### Setup

```bash
cd signbridge-frontend

# Install test dependencies (if using Vitest)
npm install -D vitest @testing-library/react @testing-library/jest-dom

# Run tests
npm test

# Run with coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

### Test Structure

```
signbridge-frontend/src/__tests__/
├── components/
│   ├── SignBridgeInterface.test.tsx
│   └── Avatar.test.tsx
├── hooks/
│   ├── useWebSocket.test.ts
│   ├── useAudioCapture.test.ts
│   └── useConversationState.test.ts
├── services/
│   └── api.test.ts
└── setup.ts                 # Test configuration
```

### Writing Tests

#### Component Tests

```typescript
// src/__tests__/components/SignBridgeInterface.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import SignBridgeInterface from '../../components/SignBridgeInterface'
import { describe, it, expect, vi } from 'vitest'

describe('SignBridgeInterface', () => {
  it('renders hearer mode button', () => {
    render(<SignBridgeInterface />)
    expect(screen.getByText('Hearer Mode')).toBeInTheDocument()
  })

  it('toggles between modes', () => {
    render(<SignBridgeInterface />)
    const deafModeBtn = screen.getByText('Deaf Mode')
    fireEvent.click(deafModeBtn)
    expect(deafModeBtn).toHaveClass('active')
  })

  it('starts recording on button press', async () => {
    render(<SignBridgeInterface />)
    const recordBtn = screen.getByText(/Press & Hold/)
    fireEvent.mouseDown(recordBtn)
    expect(recordBtn).toHaveClass('recording')
  })
})
```

#### Hook Tests

```typescript
// src/__tests__/hooks/useWebSocket.test.ts
import { renderHook, act } from '@testing-library/react'
import { useWebSocket } from '../../hooks/useWebSocket'
import { describe, it, expect, beforeEach, vi } from 'vitest'

describe('useWebSocket', () => {
  beforeEach(() => {
    // Mock WebSocket
    global.WebSocket = vi.fn(() => ({
      send: vi.fn(),
      close: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      readyState: WebSocket.OPEN
    })) as any
  })

  it('connects to WebSocket', async () => {
    const { result } = renderHook(() => useWebSocket())
    
    await act(async () => {
      await result.current.connect()
    })
    
    expect(result.current.isConnected).toBe(true)
  })

  it('sends messages', () => {
    const { result } = renderHook(() => useWebSocket())
    const message = { type: 'test', data: 'hello' }
    
    act(() => {
      result.current.send(message)
    })
    
    // Verify send was called
    expect(result.current.ws?.send).toHaveBeenCalled()
  })
})
```

#### Service Tests

```typescript
// src/__tests__/services/api.test.ts
import { apiClient } from '../../services/api'
import { vi } from 'vitest'

describe('APIClient', () => {
  it('makes health check request', async () => {
    const response = await apiClient.healthCheck()
    expect(response.status).toBe('healthy')
  })

  it('handles errors gracefully', async () => {
    // Mock error response
    const result = await apiClient.sendMessage('test').catch(e => e)
    expect(result).toBeInstanceOf(Error)
  })
})
```

### Running Tests in CI/CD

```yaml
# .github/workflows/test.yml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test -- --coverage
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Integration Tests

### WebSocket Integration

```python
# tests/test_websocket_integration.py
import pytest
import asyncio
from app.api.websocket import router

@pytest.mark.asyncio
async def test_websocket_message_flow():
    """Test complete WebSocket message flow"""
    # Simulate client connection and message exchange
    async with connect_websocket("ws://localhost:8000/ws") as ws:
        # Send audio
        await ws.send_json({
            "type": "audio",
            "data": b"audio_chunk",
            "timestamp": 1234567890
        })
        
        # Receive transcript
        response = await asyncio.wait_for(ws.receive_json(), timeout=5)
        assert response["type"] == "transcript"
        assert "text" in response["data"]
```

## Performance Testing

### Load Testing with Apache Bench

```bash
# Test API endpoint
ab -n 1000 -c 50 http://localhost:8000/health

# With custom headers
ab -n 1000 -c 50 -H "Authorization: Bearer token" \
  http://localhost:8000/api/messages
```

### Load Testing with k6

```javascript
// load-test.js
import http from 'k6/http'
import { check, sleep } from 'k6'

export let options = {
  stages: [
    { duration: '30s', target: 20 },  // Ramp up
    { duration: '1m30s', target: 10 }, // Hold
    { duration: '20s', target: 0 }     // Ramp down
  ]
}

export default function () {
  // Test health endpoint
  let res = http.get('http://localhost:8000/health')
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200
  })
  
  sleep(1)
  
  // Test WebSocket
  let ws = http.ws.connect('ws://localhost:8000/ws', function (socket) {
    socket.send(JSON.stringify({
      type: 'test',
      data: 'hello'
    }))
    
    socket.on('message', (data) => {
      check(data, {
        'received response': () => data.length > 0
      })
    })
  })
}
```

Run: `k6 run load-test.js`

## E2E Testing

### Using Playwright

```typescript
// e2e/signbridge.spec.ts
import { test, expect } from '@playwright/test'

test.describe('SignBridge E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173')
  })

  test('should load the application', async ({ page }) => {
    expect(await page.title()).toContain('SignBridge')
  })

  test('should switch between modes', async ({ page }) => {
    await page.click('button:has-text("Deaf Mode")')
    const btn = page.locator('button:has-text("Deaf Mode")')
    await expect(btn).toHaveClass(/active/)
  })

  test('should show error when backend is down', async ({ page }) => {
    // Simulate backend down
    await page.context().setExtraHTTPHeaders({
      'X-Simulate-Error': 'true'
    })
    
    await page.waitForSelector('.error-box')
    expect(await page.locator('.error-box').isVisible()).toBe(true)
  })

  test('complete conversation flow', async ({ page }) => {
    // Start recording
    await page.mouseDown('button:has-text("Press & Hold")')
    await expect(page.locator('button:has-text("Recording")')).toBeVisible()
    
    // Stop recording
    await page.mouseUp('button:has-text("Recording")')
    
    // Wait for transcript
    await page.waitForSelector('.transcript-box')
    expect(await page.locator('.transcript-box').isVisible()).toBe(true)
  })
})
```

Run: `npx playwright test`

## Coverage Goals

- **Backend**: 80% overall, 100% for critical paths
- **Frontend**: 75% overall, 100% for components
- **E2E**: Critical user journeys covered

## Debugging Tests

### Backend

```bash
# Run with print statements
pytest -s -v

# Run with debugger
pytest --pdb

# Run specific test
pytest tests/test_api.py::test_health_check -v -s
```

### Frontend

```bash
# Run in watch mode
npm test -- --watch

# Generate coverage report
npm test -- --coverage

# Debug in browser
npm test -- --debug
```

## CI/CD Integration

Tests run automatically on:
- Pull Requests
- Commits to main/develop
- Scheduled nightly runs

Failed tests block merges to main.

---

See [project-details.MD](./project-details.MD) for testing requirements in the specification.
