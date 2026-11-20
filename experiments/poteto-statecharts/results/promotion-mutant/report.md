# ImagePromotion

TLC reached 7 states and 8 steps. The chart draws 7 states and 7 arrows.
The chart does not draw 1 steps that stay in one chart state.

## NoUnapprovedRuntime breaks
The shortest path has 4 steps:
0. Original source and running image
1. merge source change: Source merged; old image running
2. build and test image: Image tested; old image running
3. publish digest: Image published; old image running
4. Argo reconciles main: New image running without promotion

## Rules that hold
NoDeadlock
