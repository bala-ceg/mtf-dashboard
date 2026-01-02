import pandas as pd

def extract_market_summary(csv_path):
    raw = pd.read_csv(csv_path, header=None)

    mapping = {
        "scripwise total outstanding on the beginning of the day": "opening",
        "fresh exposure taken during the day": "fresh",
        "exposure liquidated during the day": "liquidated",
        "net scripwise outstanding at the end of the day": "closing",
    }

    values = {v: None for v in mapping.values()}

    for key, field in mapping.items():
        # Search in all columns for matching text (case-insensitive)
        for col_idx in range(raw.shape[1]):
            row = raw[
                raw[col_idx].astype(str).str.lower().str.contains(key, na=False)
            ]
            if not row.empty:
                try:
                    # Try to extract value from the column to the right of the match
                    if col_idx + 1 < raw.shape[1]:
                        val_str = str(row.iloc[0, col_idx + 1]).strip()
                        if val_str and val_str.lower() != 'nan':
                            values[field] = float(val_str)
                            break
                except (ValueError, IndexError, TypeError):
                    pass

    if all(v is None for v in values.values()):
        return None

    def to_cr(v):
        return v / 100 if v is not None else None

    return {
        "opening_outstanding_cr": to_cr(values["opening"]),
        "fresh_exposure_cr": to_cr(values["fresh"]),
        "liquidated_exposure_cr": to_cr(values["liquidated"]),
        "closing_outstanding_cr": to_cr(values["closing"]),
    }
