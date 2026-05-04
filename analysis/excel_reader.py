import pandas as pd
import io


def load_excel(file_obj):
    filename = getattr(file_obj, "name", str(file_obj))
    if filename.endswith(".csv"):
        df = pd.read_csv(file_obj)
        return _clean_df(df), []

    raw_bytes   = file_obj.read()
    xl          = pd.ExcelFile(io.BytesIO(raw_bytes))
    sheet_names = xl.sheet_names
    df          = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=0)
    return _clean_df(df), sheet_names


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df.reset_index(drop=True)


def get_column_summary(df: pd.DataFrame) -> str:
    lines = [f"The dataset has {len(df)} rows and {len(df.columns)} columns:"]
    for col in df.columns:
        sample = df[col].dropna().head(3).tolist()
        lines.append(f"  - '{col}' ({df[col].dtype}): e.g. {sample}")
    return "\n".join(lines)