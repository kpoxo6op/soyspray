------------------------- MODULE IntakeRecovery -------------------------
EXTENDS Naturals
CONSTANT AllowCrash
VARIABLES phase, worker, crashes
vars == <<phase, worker, crashes>>

Init == /\ phase = "Verified staging"
        /\ worker = "Running"
        /\ crashes = 0
WriteMarker == /\ worker = "Running" /\ phase = "Verified staging"
               /\ phase' = "Marker written"
               /\ UNCHANGED <<worker, crashes>>
Publish == /\ worker = "Running" /\ phase = "Marker written"
           /\ phase' = "Published writable"
           /\ UNCHANGED <<worker, crashes>>
Seal == /\ worker = "Running" /\ phase = "Published writable"
        /\ phase' = "Published read-only"
        /\ UNCHANGED <<worker, crashes>>
Crash == /\ AllowCrash /\ worker = "Running" /\ crashes = 0
         /\ worker' = "Stopped" /\ crashes' = 1
         /\ UNCHANGED phase
Retry == /\ worker = "Stopped"
         /\ worker' = IF phase \in {"Marker written", "Published writable"}
                       THEN "Retry rejected" ELSE "Running"
         /\ UNCHANGED <<phase, crashes>>
Done == /\ (phase = "Published read-only" \/ worker = "Retry rejected")
        /\ UNCHANGED vars
Next == WriteMarker \/ Publish \/ Seal \/ Crash \/ Retry \/ Done
RetryRecovers == worker # "Retry rejected"
=============================================================================
