# T03: Adopt the domain, one rule at a time

Make the existing code use the domain from T01. Behaviour must not change: the existing tests stay green after every subtask. DTOs stay (decision 2); mappers translate.

Subtasks, in order (statuses are in each file; `docs/tasks/status.py` summarises):

1. [S01: DTO <-> domain mappers](S01-mappers.md)
2. [S02: decide() uses the entities and the chain operations](S02-agent-chain.md)
3. [S03: Movement rules in the stepper adapter and move_arms](S03-movement.md)
4. [S04: Health rules (route and preflight)](S04-health.md)
5. [S05: Text and audio-format rules in the bridges](S05-text-and-audio-format.md)
6. [S06: CountedTextStream uses TextSegmentCounter](S06-text-segment-counter.md)
7. [S07: VoicePipelineSettings and ProgressMessages from the domain](S07-settings-and-progress.md)
8. [S08: Error classification from the domain](S08-service-errors.md)
9. [S09: Retire domain/models.py](S09-retire-models-py.md)
