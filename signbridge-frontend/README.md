# SignBridge Frontend

React + TypeScript + Vite frontend for SignBridge Live application.

## Features

- Real-time bidirectional communication between deaf and hearing users
- WebSocket-based streaming for audio and video
- 3D avatar rendering using Three.js
- WebRTC for camera and audio capture
- TypeScript for type safety

## Getting Started

### Prerequisites

- Node.js 16+ and npm/yarn/pnpm

### Installation

```bash
npm install
```

### Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build

Build for production:

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

## Project Structure

```
src/
├── components/        # React components
├── services/         # API and WebSocket services
├── hooks/           # Custom React hooks
├── types/           # TypeScript type definitions
├── utils/           # Utility functions
├── pages/           # Page components
├── styles/          # CSS files
├── App.tsx          # Root component
└── main.tsx         # Entry point
```

## Environment Variables

Create a `.env` file in the root directory:

```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/signbridge
VITE_VIDEO_FRAME_INTERVAL_MS=300
```

## Technologies Used

- **React 18**: UI framework
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool
- **Three.js**: 3D graphics for avatar rendering
- **Axios**: HTTP client
- **WebSocket**: Real-time communication
- **WebRTC**: Audio/video streaming

## License

MIT
