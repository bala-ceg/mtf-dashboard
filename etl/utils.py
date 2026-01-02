import pandas as pd

def read_scripwise_table(csv_path):
    raw = pd.read_csv(csv_path, header=None)

    header_row = None
    for i, row in raw.iterrows():
        if str(row[0]).strip().lower() == "symbol":
            header_row = i
            break

    if header_row is None:
        raise ValueError(f"'Symbol' header not found in {csv_path.name}")

    df = pd.read_csv(csv_path, skiprows=header_row)

    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^\w]", "", regex=True)
    )

    df = df.loc[:, ~df.columns.str.startswith("unnamed")]
    df.dropna(subset=["symbol"], inplace=True)

    return df