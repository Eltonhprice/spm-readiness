# scripts/status.py


def measured(value, **kwargs):
    d = {"value": value, "status": "measured"}
    d.update(kwargs)
    return d


def not_collected(note=""):
    return {"value": None, "status": "not_collected", "note": note}


def not_applicable(note=""):
    return {"value": None, "status": "not_applicable", "note": note}


def pct(numerator, denominator):
    if not denominator:
        return None
    return round(100.0 * numerator / denominator, 1)
