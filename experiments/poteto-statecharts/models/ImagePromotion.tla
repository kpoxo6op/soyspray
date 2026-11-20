------------------------- MODULE ImagePromotion -------------------------
EXTENDS Naturals
CONSTANT AutoDeploySource
VARIABLES source, artifact, approved, declared, running
vars == <<source, artifact, approved, declared, running>>
Init == /\ source = "Old" /\ artifact = "Absent" /\ approved = FALSE
        /\ declared = "Old" /\ running = "Old"
MergeSource == /\ source = "Old" /\ source' = "New"
               /\ UNCHANGED <<artifact, approved, declared, running>>
BuildAndTest == /\ source = "New" /\ artifact = "Absent" /\ artifact' = "Tested"
                /\ UNCHANGED <<source, approved, declared, running>>
PublishImage == /\ artifact = "Tested" /\ artifact' = "Published"
                /\ declared' = IF AutoDeploySource THEN "New" ELSE declared
                /\ UNCHANGED <<source, approved, running>>
MergePromotion == /\ artifact = "Published" /\ ~approved
                  /\ approved' = TRUE /\ declared' = "New"
                  /\ UNCHANGED <<source, artifact, running>>
Reconcile == /\ declared = "New" /\ running = "Old" /\ running' = "New"
             /\ UNCHANGED <<source, artifact, approved, declared>>
Done == /\ running = "New" /\ approved /\ UNCHANGED vars
Next == MergeSource \/ BuildAndTest \/ PublishImage \/ MergePromotion \/ Reconcile \/ Done
NoUnapprovedRuntime == running = "New" => approved
=============================================================================
