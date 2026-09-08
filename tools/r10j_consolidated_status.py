"""Build the R.10J Markdown report from its structured status source.

This module has no executable entry point.  It performs presentation only and
cannot access data, run research, grant approval, or change lifecycle state.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def _cell(value: Any) -> str:
    return str(value).replace("|", "/").replace("\n", " ")


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(_cell(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def _bullets(values: Sequence[str]) -> str:
    return "\n".join(f"- {value}" for value in values)


def render_status_markdown(status: Mapping[str, Any]) -> str:
    control = status["document_control"]
    sync = control["synchronization"]
    readiness = status["current_readiness"]
    milestones = status["milestones"]
    sources = status["data_sources"]
    validation = status["validation"]
    next_stage = status["proposed_next_milestone"]
    review = status["owner_review"]

    pages: list[str] = []
    pages.append(f"""# {control['title']}

## Document control

{_table(['Field', 'Value'], [
    ['Milestone', control['milestone']],
    ['Document version', control['document_version']],
    ['Generation date', control['generation_date']],
    ['Repository / branch', f"custom_terminal / {control['branch']}"],
    ['Exact source commit', control['source_commit']],
    ['Remote synchronization', sync['status']],
    ['Evidence classification', control['evidence_classification']],
    ['Owner-review status', control['owner_review_status']],
    ['Next-task approval', control['next_task_approval_status']],
])}

{control['warning']}

This is an owner-status document. It records evidence and asks for decisions;
it does not grant permission to perform the next task.
""")
    pages.append("""# Table of contents

| Section | Page |
|---|---:|
| Executive summary | 3 |
| What we are trying to build | 4 |
| What has been completed: foundation | 5 |
| What has been completed: synthetic platform and governance | 6 |
| Data sources: access and coverage I | 7 |
| Data sources: access and coverage II | 8 |
| Data sources: qualification and allowed use I | 9 |
| Data sources: qualification and allowed use II | 10 |
| What remains blocked or unknown | 11 |
| Test and evidence status | 12 |
| Safety and authority boundaries | 13 |
| Proposed next development stage | 14 |
| Owner review and separate decisions | 15 |

Status vocabulary: **PASS** means directly demonstrated for the stated scope;
**BLOCKED** means a required gate prevents progression; **NOT QUALIFIED** means
available evidence has not passed the trust contract; **NOT APPLICABLE** means
the source or capability does not address that question.
""")
    pages.append(f"""# Executive summary

The project is building an analysis-only decision-support system for Indian
markets. Its eventual visible outputs may include a market-sentiment score and
individual stock scores, but only when those values can be traced to clean,
point-in-time data and genuinely out-of-sample evidence.

The engineering machinery is substantially proven on fictional data. It can
preserve source vintages, calculate deterministic features and outcomes, run
walk-forward validation, separate predictive/economic/portfolio evidence, and
publish immutable noncanonical artifacts. This does **not** prove that any
market edge exists.

Current market-data readiness remains blocked. The broad equity directory is
survivor-selected; the official NSE population sample qualified only 3 of 12
dated security/bhavcopy pairs; terminal outcomes, stable identity, corporate
actions, benchmarks and historical costs remain incomplete. Momentum v1 is not
validated or actionable.

{_table(['Readiness area', 'Current state'], [[k.replace('_', ' ').title(), v] for k, v in readiness.items()])}

The single proposed next stage is `{next_stage['id']}`. It is a bounded
qualification task for an already-local candidate source, not a backtest. It
requires a separate owner decision after this report is reviewed.
""")
    pages.append(f"""# What we are trying to build

The target is a trustworthy research and capital-allocation support system,
not a trading bot. Deterministic code remains the numerical source of truth;
AI may explain evidence and propose hypotheses but may not invent scores or
override validation.

{_table(['Layer', 'Responsibility', 'Required evidence'], [
    ['Data ingestion', 'Acquire immutable source objects through replaceable providers.', 'Source identity, retrieval time, hashes, terms and parser version.'],
    ['Data qualification', 'Normalize typed facts and test completeness, identity and timing.', 'PASS/FAIL/UNKNOWN capabilities with evidence.'],
    ['Research', 'Declare hypotheses, universes, features and executable outcomes.', 'Pre-registration and point-in-time inputs.'],
    ['Validation', 'Use walk-forward folds, purge/embargo, costs and untouched holdouts.', 'Out-of-sample prediction, economic and portfolio diagnostics.'],
    ['Scoring', 'Calibrate validated predictions and keep confidence separate.', 'Comparable historical buckets, uncertainty, decay and lifecycle.'],
    ['Presentation', 'Expose approved evidence and limitations without recalculation.', 'Immutable read models and provenance.'],
    ['Trading', 'Outside project scope.', 'No order placement, modification or cancellation.'],
])}

Intended scores remain richer than a number: raw prediction, confidence,
regime, horizon, contributors, risks and behavior of comparable historical
scores must remain visible. Missing evidence cannot be converted into a neutral
score.

Standing owner decisions include: no paid market-data providers; preference
for relevant free official sources; version2.0 remains separate; scores remain
hidden until supported; the local F&O database may be audited later; portfolio
and some presentation choices remain deferred; and the project must never
execute trades.
""")
    pages.append("# What has been completed - foundation\n\n" + _table(
        ["Milestone", "Status", "Evidence-backed result"],
        [[m["id"], m["status"], m["result"]] for m in milestones[:6]],
    ) + """

## Momentum v1 status

The legacy experiment was rejected in its original archive. The new Slice A
reproduced mechanics on a controlled fixture, but the available broad dataset
failed survivorship and provenance gates. Apparent results on that directory
cannot confirm the hypothesis. Momentum is neither `VALIDATED` nor `ACTIVE`,
and it emits no BUY/HOLD/REDUCE recommendation.

## Evidence categories

- **Mechanically validated infrastructure:** deterministic contracts and tests.
- **Synthetic-only evidence:** fictional known-answer fixtures, noncanonical.
- **Historically trustworthy market evidence:** not yet sufficient.
- **Economically validated edges:** none.
""")
    pages.append("# What has been completed - synthetic platform and governance\n\nAll items on this page are engineering evidence from fictional inputs, not market findings.\n\n" + _table(
        ["Milestone", "Status", "Evidence-backed result"],
        [[m["id"], m["status"], m["result"]] for m in milestones[6:]],
    ) + f"""

The R10A holdout remains `{validation['r10a_holdout']}`. Synthetic successes
prove that the engines respond correctly to declared known answers and failure
challenges. They do not estimate a real return, validate a market relationship,
or justify a score.
""")

    access_headers = ["Source", "Cost/access", "Current availability", "Historical depth", "Primary purpose"]
    access_rows = lambda batch: [[s["source"], s["cost"], s["availability"], s["historical_depth"], s["purpose"]] for s in batch]
    pages.append("# What data we currently have - access and coverage I\n\nAvailability describes what is present or identified; it does not establish research fitness.\n\n" + _table(access_headers, access_rows(sources[:5])) + """

The existing broad equity directory is **not sufficient** to approve a
cross-sectional edge. Long date coverage and many files do not compensate for
omitted historical securities, unresolved identities or missing terminal
economics.
""")
    pages.append("# What data we currently have - access and coverage II\n\nThese sources supplement specific current, benchmark or cost questions; none closes historical equity-population gaps.\n\n" + _table(access_headers, access_rows(sources[5:])) + """

Kite current instruments are not a historical universe and cannot validate
historical cross-sectional research. AMFI is relevant to mutual funds, not to
equity population or security identity. The local F&O database is not trusted
merely because it exists.
""")
    qual_headers = ["Source", "Survivorship / terminal", "Corporate actions", "Qualification", "Allowed vs prohibited"]
    qual_rows = lambda batch: [[s["source"], f"{s['survivorship']}; terminal: {s['terminal_states']}", s["corporate_actions"], s["qualification"], f"Allowed: {s['approved_use']}. Prohibited/unproven: {s['prohibited_or_unproven']}."] for s in batch]
    pages.append("# Data qualification and allowed use I\n\nQualification remains source- and purpose-specific. Missing capabilities stay explicit.\n\n" + _table(qual_headers, qual_rows(sources[:5])) + """

Technical accessibility is not permission, and permission is not completeness.
Every source must pass both evidence-quality and lawful-retention gates before
canonical research can use it.
""")
    pages.append("# Data qualification and allowed use II\n\nCurrent access or conceptual methodology does not imply qualified historical research evidence.\n\n" + _table(qual_headers, qual_rows(sources[5:])) + """

NSE and BSE listings remain distinct. Issuer-name or ticker similarity cannot
merge them. Current rates cannot be carried backward into historical cost
schedules. PRI cannot be silently substituted for TRI.
""")
    pages.append("# What remains blocked or unknown\n\n" + _bullets(status["blocked_or_unknown"]) + """

No defensible continuous historical start date has been promoted. Missing
delisting consideration remains unresolved; a last quoted price is not an
economic terminal value. A selected set of circulars is not a complete event
ledger.

Scores are planning concepts only. Market-sentiment inputs represent different
economic objects and clocks; stock-score categories have distinct data and
leakage risks. No aggregation weights, calibration or recommendation semantics
have been approved.
""")
    pages.append(f"""# Test and evidence status

The latest completed suites and evidence checks establish engineering integrity within their declared scopes.

{_table(['Check', 'Latest verified status'], [[k.replace('_', ' ').title(), v] for k, v in validation.items() if k not in ('r10i_authoritative_git_fingerprint',)])}

Authoritative R10I Git-object fingerprint (280 policy-v2 files):

```
{validation['r10i_authoritative_git_fingerprint']}
```

R10I.1 proved that `e0870bd...` was a stale pre-refresh working-tree value and
`236fddae...` was a post-refresh working-tree value. Neither is presented as a
commit fingerprint. The immutable implementation and evidence commits both
reproduce the full hash above.

These tests prove deterministic mechanics, preservation, contracts and
fail-closed boundaries. They do **not** prove market-data completeness,
representative distributions, scalable production performance, profitability,
or an economically valid edge.
""")
    pages.append(f"""# Safety and authority boundaries

{control['warning']}

{_table(['Boundary', 'Authorized?'], [[k.replace('_', ' ').title(), 'YES' if v else 'NO'] for k, v in status['safety_boundaries'].items()])}

- Analysis-only product; no trade execution and no broker orders.
- No promotion or display of unsupported scores.
- No silent use of private or paid data.
- No R10A holdout consumption without separate exact authorization.
- No live-broker code change in this milestone.
- No real-data research authority arises from generating or approving this status report.

The application implements a narrow Kite read-only allowlist, but an account
token may possess broader provider permissions. The claim is about application
behavior, not about the theoretical capabilities of the token.
""")
    pages.append(f"""# Proposed next development stage

This proposal is presented for a separate owner decision and is not active work.

## {next_stage['id']}

Recommendation: **{next_stage['recommendation']}**

{next_stage['reason']}

### Preliminary scope

{_bullets(next_stage['scope'])}

### Explicit exclusions and abort boundary

{_bullets(next_stage['exclusions'])}

Status: `{next_stage['authorization']}`

This is the narrowest useful next qualification step because it can determine
whether an already-local candidate source deserves any later research use. It
does not require a new external download and does not test a trading idea. If
read-only safety or bounded inspection cannot be established, the stage stops
and reports that blocker.
""")
    pages.append(f"""# Owner review - separate decisions required

{control['warning']}

## Facts to confirm

- The report accurately separates synthetic machinery readiness from real-data and economic readiness.
- No market edge or score is currently validated or actionable.
- Paid market-data providers remain prohibited.
- Kite remains current-only; AMFI is not equity-population evidence.
- The local F&O database remains unqualified.
- The project remains analysis-only and must never execute trades.

## Material risks

Historical population, identity, terminal outcomes, corporate actions,
benchmarks, cost schedules, provider rights and real-data reproducibility remain
materially incomplete. A readable database may still fail qualification.

## Decision A - report accuracy

[ ] Approve this report as an accurate status summary.  [ ] Request corrections.

Corrections / affected section: ____________________________________________

## Decision B - proposed next milestone

[ ] Separately approve `{next_stage['id']}`.  [ ] Do not approve it yet.

[ ] Pause development.

Owner name/signature: ____________________  Date: ____________________

Initial machine state: report approval `{review['report_accuracy_approval']}`;
next-task approval `{review['next_milestone_approval']}`. Approval of Decision A
does not imply approval of Decision B. Neither choice authorizes research,
backtesting, scoring, recommendations or trading.
""")
    return "\n\n[PAGE BREAK]\n\n".join(page.strip() for page in pages) + "\n"
