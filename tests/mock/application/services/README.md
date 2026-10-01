# Application Service Tests

- `test_brain_service.py`: the public `BrainService` methods with fake ports (batch and microphone transcription, text
  playback, the voice pipeline, the movement of an arm).
- `test_agent_service.py`: `decide()`, the chain of ai-agent's flows: order, the flow that waits for the user, flows that
  cannot be reached, the movements and their order. `test_agent_service_invalid_movement.py`: a movement the domain does
  not accept stops the sequence and the speech is kept.
- `test_agent_flow_session.py`: opening, asking and ending a session, and the reconnect on `SESSION_NOT_FOUND`.
- `test_health_service.py`: the two-stage health check (`/health` then `/available`).
- `test_progress_messages.py`: "Message received." at once and "Thinking." every interval while the flows work.

## Run

```powershell
python -m pytest tests/mock/application/services
```