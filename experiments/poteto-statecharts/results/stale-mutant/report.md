# StaleOperation

TLC reached 7 states and 9 steps. The chart draws 7 states and 6 arrows.
The chart does not draw 3 steps that stay in one chart state.

## NeverTerminateNewOperation breaks
The shortest path has 3 steps:
0. Reviewed operation: Read checked
1. re-read operation: Reviewed operation: Patch ready
2. controller starts a new operation: New operation: Patch ready
3. submit termination request: New operation: Applied

## Rules that hold
NoDeadlock
