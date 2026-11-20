------------------------- MODULE StaleOperation -------------------------
EXTENDS Naturals
CONSTANT UseVersionGuard
VARIABLES version, operation, stage, terminatedNew
vars == <<version, operation, stage, terminatedNew>>
Init == /\ version = 1 /\ operation = "Reviewed operation"
        /\ stage = "Read checked" /\ terminatedNew = FALSE
Reread == /\ stage = "Read checked"
          /\ stage' = IF version = 1 THEN "Patch ready" ELSE "Stopped"
          /\ UNCHANGED <<version, operation, terminatedNew>>
Replace == /\ operation = "Reviewed operation" /\ stage \in {"Read checked", "Patch ready"}
           /\ version' = 2 /\ operation' = "New operation"
           /\ UNCHANGED <<stage, terminatedNew>>
Patch == /\ stage = "Patch ready"
         /\ stage' = IF UseVersionGuard /\ version # 1 THEN "Conflict" ELSE "Applied"
         /\ terminatedNew' = (operation = "New operation" /\ (~UseVersionGuard \/ version = 1))
         /\ UNCHANGED <<version, operation>>
Done == /\ stage \in {"Stopped", "Conflict", "Applied"} /\ UNCHANGED vars
Next == Reread \/ Replace \/ Patch \/ Done
NeverTerminateNewOperation == ~terminatedNew
=============================================================================
