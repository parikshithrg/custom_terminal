# R10L Governance Remediation

R10M removes the repository-wide pytest collection hook that converted an obsolete current-checkout assertion into an expected failure. No xfail remains.

The R9L statement was true when generated: commit `d0102dc` does not contain `pre_research_review_record_v6.json`, and the exact historical R9L test has SHA-256 `11433b539d098cd7a057175ff26393ca45e50718fe8cd4459392a69c4582f3a5`. The later review remains valid current evidence: it postdates the generation manifest and authorizes only `LOCAL_FNO_DATABASE_READ_ONLY_QUALIFICATION_STAGE_1`. It does not rewrite R9L and cannot authorize R10M or a future production scope.

Forward tests now read immutable historical bytes from the correct Git tree. R10L manifest bindings are likewise checked against sealed commit `09cf0cb`, allowing a current forward test to evolve without modifying the historical commit.

This is a temporal-model correction, not a weakening of the gate. R9D remains closed, the local database was not opened, and no new data, research, dependency, broker or trading authority was granted.
