# Contributing to SignBridge Live

Thank you for your interest in contributing! This guide will help you get started.

## Code of Conduct

- Be respectful and inclusive
- Focus on the code, not the person
- Help others learn and grow
- Report issues constructively

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/SignBridge.git
cd SignBridge
```

### 2. Set Up Development Environment

Follow [BUILD.md](./BUILD.md) for setup instructions.

### 3. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/avatar-animation` - new features
- `fix/websocket-reconnect` - bug fixes
- `docs/installation-guide` - documentation
- `refactor/api-cleanup` - code refactoring

## Development Workflow

### Before You Start

1. Check existing issues and PRs to avoid duplicates
2. Discuss major changes in an issue first
3. Ensure your code follows the project style guide

### Backend Development

```bash
cd signbridge-backend
source venv/bin/activate

# Make your changes
# ...

# Run tests
pytest

# Format code
black app/
isort app/

# Type check
mypy app/

# Lint
flake8 app/
```

**Code Style:**
- Use Black for formatting
- Follow PEP 8
- Add type hints to functions
- Write docstrings for public functions
- Keep functions focused and small

### Frontend Development

```bash
cd signbridge-frontend

# Make your changes
# ...

# Format code
npm run format

# Lint
npm run lint

# Type check
npx tsc --noEmit

# Run tests
npm test
```

**Code Style:**
- Use Prettier for formatting
- Follow ESLint rules
- Use TypeScript, avoid `any`
- Component names in PascalCase
- Use functional components with hooks
- Keep components small and focused

## Commit Guidelines

### Commit Messages

```
[TYPE] Brief description (50 chars max)

Longer explanation if needed, wrapped at 72 characters.
Explain the problem being solved and why this solution.

Fixes #123
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Code style (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Dependencies, configuration

### Examples

```
feat: Add WebSocket reconnection logic
fix: Correct audio streaming delay
docs: Update deployment instructions
refactor: Simplify avatar animation logic
test: Add WebSocket connection tests
```

## Pull Request Process

1. **Ensure quality:**
   - All tests pass: `pytest` (backend), `npm test` (frontend)
   - No linting errors: `black`, `flake8`, `npm run lint`
   - Type checks pass: `mypy`, `npx tsc --noEmit`

2. **Update documentation:**
   - Add docstrings for new functions
   - Update README.md if needed
   - Add inline comments for complex logic

3. **Create descriptive PR:**
   ```markdown
   ## Description
   Brief explanation of what this PR does

   ## Related Issues
   Fixes #123

   ## Type of Change
   - [ ] New feature
   - [ ] Bug fix
   - [ ] Documentation update

   ## Testing
   Describe how to test your changes

   ## Checklist
   - [ ] Tests pass
   - [ ] Code is formatted
   - [ ] No breaking changes
   - [ ] Documentation updated
   ```

4. **Wait for review:**
   - Respond to feedback promptly
   - Request changes explicitly if needed
   - Keep commits clean (squash if necessary)

## Testing Guidelines

### Backend Tests

```bash
cd signbridge-backend

# Test structure
tests/
├── test_api.py           # API endpoint tests
├── test_services.py      # Service layer tests
├── test_agents.py        # Agent tests
└── conftest.py           # Shared fixtures
```

Write tests for:
- New endpoints
- Service methods
- Edge cases and error handling
- WebSocket interactions

### Frontend Tests

```bash
cd signbridge-frontend

# Test structure
src/__tests__/
├── components/           # Component tests
├── hooks/               # Hook tests
└── services/            # Service tests
```

Write tests for:
- Component rendering
- User interactions
- Hook behavior
- Error states

## Documentation

### Code Comments

```python
def calculate_animation_duration(frame_count: int) -> float:
    """Calculate duration based on frame count.
    
    Args:
        frame_count: Number of animation frames
        
    Returns:
        Duration in seconds
    """
```

### README Updates

If adding features, update relevant README sections:
- `signbridge-backend/README.md`
- `signbridge-frontend/README.md`
- Main `README.md`

### Type Definitions

Keep TypeScript types in `src/types/` properly documented:

```typescript
/** Represents a real-time message in the system */
export interface Message {
  type: 'audio' | 'video' | 'text' | 'transcript'
  timestamp: number
  data: unknown
}
```

## Debugging

### Backend Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Use Python debugger
import pdb; pdb.set_trace()

# Check logs
docker-compose logs backend -f
```

### Frontend Debugging

```bash
# Use browser DevTools
# F12 or Ctrl+Shift+I

# Set breakpoints in VS Code
# Debug configuration in .vscode/launch.json

# Check network tab for WebSocket issues
```

## Performance Considerations

### Backend

- Profile with `cProfile` for bottlenecks
- Monitor WebSocket memory usage
- Keep response times under 100ms
- Batch database operations

### Frontend

- Minimize re-renders with `React.memo`, `useMemo`
- Code-split components with `React.lazy`
- Monitor bundle size
- Use DevTools Performance tab

## Security

- Never commit secrets or credentials
- Use environment variables for config
- Validate all inputs (frontend and backend)
- Keep dependencies updated
- Report security issues privately

## Reporting Issues

### Bug Reports

```markdown
## Description
Brief description of the bug

## Steps to Reproduce
1. ...
2. ...
3. ...

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: Windows/macOS/Linux
- Browser: Chrome/Firefox
- Node version: ...
- Python version: ...
```

### Feature Requests

```markdown
## Description
What feature or improvement?

## Use Case
Why is this needed?

## Proposed Solution
How should it work?

## Alternatives
Other possible approaches?
```

## Getting Help

- **Questions**: Open a Discussion
- **Bugs**: File an Issue
- **Security**: Email security@signbridge.dev
- **Chat**: Join our Discord

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md
- Release notes
- GitHub contributors graph

---

**Thank you for contributing to SignBridge Live! 🎉**
