# IntakeRecovery

TLC reached 14 states and 19 steps. The chart draws 10 states and 11 arrows.
The chart does not draw 5 steps that stay in one chart state.

## RetryRecovers breaks
The shortest path has 3 steps:
0. Verified staging
1. write completion marker: Marker written
2. process stops: Marker written: Stopped
3. retry same archive: Marker written: Retry rejected

## Rules that hold
NoDeadlock
