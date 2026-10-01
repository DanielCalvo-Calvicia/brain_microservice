# T04: Application layout

Split the ports and the BrainService, create the streams package and rename `routes/` to `voice_pipeline/` (decision 1: yes). Every move comes with its import rewrite, done by script, and ends green.

Subtasks, in order (statuses are in each file; `docs/tasks/status.py` summarises):

1. [S01: Split the ports](S01-ports-split.md)
2. [S02: Split BrainService into a facade and four services](S02-split-brain-service.md)
3. [S03: streams/ package](S03-streams-package.md)
4. [S04: routes/ becomes voice_pipeline/ (steps/ and bridges/)](S04-voice-pipeline-rename.md)
