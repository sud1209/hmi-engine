"""Shared sentiment extraction utility."""

_BULLISH = {"bullish", "positive", "optimistic", "strong", "growing", "upward"}
_BEARISH = {"bearish", "negative", "pessimistic", "weak", "declining", "downward"}


def extract(text: str) -> str:
    """Return 'Bullish', 'Bearish', or 'Neutral' from free-form text."""
    lower = text.lower()
    bull = sum(1 for w in _BULLISH if w in lower)
    bear = sum(1 for w in _BEARISH if w in lower)
    if bull > bear:
        return "Bullish"
    if bear > bull:
        return "Bearish"
    return "Neutral"
