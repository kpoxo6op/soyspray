# GI v4 development

GI v2 remains the deployed model. It is usable but not fully reliable. GI v3
was rejected. GI v4 is an optional later improvement and has not been trained
or deployed.

The v4 workflow is reproducible by code:

- `gi_v4_synthesis_plan.py` creates 44,000 deterministic synthetic records.
- `gi_v4_synthesize.py` renders an atomic generated tree and records each WAV
  hash.
- `gi-v4-train.patch` selects one model only when all training gates pass.
- `gi_v4_stream_eval.py` tests the production threshold, cumulative trigger,
  and refractory behavior.
- `gi_v4_browser_checkpoints.py` uses v4-only transfer names and provenance.
- `train_gi_v4_colab.py` connects generation, training, conversion, evaluation,
  and bundling.

The workflow does not accept human audio as a training or stream-input source.
The final bundle records the model, synthesis evidence, public negative feature
set, evaluator, runtime settings, gates, and report hashes.

## Later procedure

1. Add a small Colab launcher that pins the reviewed Git commit.
2. Run `generate`, `augment`, `train`, and `finish` on a free Colab GPU.
3. Save each verified browser checkpoint outside the Colab runtime.
4. Test the frozen model with private held-out voice recordings locally.
5. Promote the model through GitOps only if the automatic and device checks
   pass.

Keep GI v2 available for rollback. Do not lower its live threshold as a
substitute for a better candidate.

Optional later work can add more report-tampering tests and a larger held-out
voice corpus. These items are not required for the current GI v2 deployment.
