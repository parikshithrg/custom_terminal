"""Headline sentiment - VADER's engine (handles negation/intensifiers
well) augmented with a hand-built finance lexicon, NOT plain VADER and
NOT Loughran-McDonald on their own.

Tested live against real headlines from this project's own News Feed
before choosing this, 2026-08-18 - plain VADER scored "Gold Slips on
Higher Oil" positive (+0.20) and "European shares decline" strongly
positive (+0.60), because it has no finance vocabulary. Loughran-McDonald
(the academic finance-sentiment standard, built from 10-K filings)
correctly read "downgrades" and "decline" as negative but scored "surge,"
"slips," and "rise" all as neutral (0.0) - it was built for long filing
text, not short headline verbs, so its coverage on news headlines
specifically is poor. The hybrid below fixed both real failures on the
same test headlines - see [[project-local-terminal-status]]'s 2026-08-18
entry for the full before/after comparison.

NOT PERFECT on genuinely mixed headlines (a headline with both a positive
and negative clause can still land on the wrong side) - stated plainly,
not oversold. Standard VADER threshold convention: compound >= 0.05
Positive, <= -0.05 Negative, else Neutral.
"""

from __future__ import annotations

from functools import lru_cache

# Verbs/adjectives common in market headlines that generic VADER doesn't
# carry (or carries wrong) - polarity strengths hand-set on the same -4..+4
# scale VADER's own lexicon uses, not fitted against any labelled dataset.
FINANCE_LEXICON: dict[str, float] = {
    "surge": 2.5, "surges": 2.5, "surged": 2.5, "surging": 2.5,
    "soar": 2.8, "soars": 2.8, "soared": 2.8, "soaring": 2.8,
    "rally": 2.2, "rallies": 2.2, "rallied": 2.2, "rallying": 2.2,
    "jump": 2.0, "jumps": 2.0, "jumped": 2.0, "jumping": 2.0,
    "gain": 1.5, "gains": 1.5, "gained": 1.5, "gaining": 1.5,
    "rise": 1.3, "rises": 1.3, "rose": 1.3, "rising": 1.3,
    "upgrade": 2.0, "upgrades": 2.0, "upgraded": 2.0,
    "outperform": 1.8, "buy": 1.2, "bullish": 2.0,
    "beat": 1.5, "beats": 1.5, "record": 1.3, "strong": 1.2, "growth": 1.0,
    "slip": -1.8, "slips": -1.8, "slipped": -1.8, "slipping": -1.8,
    "fall": -1.8, "falls": -1.8, "fell": -1.8, "falling": -1.8,
    "decline": -2.0, "declines": -2.0, "declined": -2.0, "declining": -2.0,
    "plunge": -2.8, "plunges": -2.8, "plunged": -2.8, "plunging": -2.8,
    "tumble": -2.5, "tumbles": -2.5, "tumbled": -2.5, "tumbling": -2.5,
    "slump": -2.3, "slumps": -2.3, "slumped": -2.3,
    "downgrade": -2.0, "downgrades": -2.0, "downgraded": -2.0,
    "underperform": -1.8, "sell": -1.2, "bearish": -2.0,
    "miss": -1.5, "misses": -1.5, "missed": -1.5, "weak": -1.2,
    "concern": -1.0, "concerns": -1.0,
    "crash": -2.8, "crashes": -2.8, "crashed": -2.8,
    "selloff": -2.0, "sell-off": -2.0,
    "losses": -1.5, "loss": -1.3, "cut": -1.3, "cuts": -1.3,
    "default": -2.2, "recession": -2.0,
}


@lru_cache(maxsize=1)
def _analyzer():
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    a = SentimentIntensityAnalyzer()
    a.lexicon.update(FINANCE_LEXICON)
    return a


def score_text(text: str) -> float:
    """Compound sentiment, -1 (most negative) to +1 (most positive)."""
    if not text:
        return 0.0
    return _analyzer().polarity_scores(text)["compound"]


def sentiment_label(score: float) -> str:
    if score >= 0.05:
        return "Positive"
    if score <= -0.05:
        return "Negative"
    return "Neutral"


def sentiment_emoji(score: float) -> str:
    if score >= 0.05:
        return "🟢"
    if score <= -0.05:
        return "🔴"
    return "⚪"
