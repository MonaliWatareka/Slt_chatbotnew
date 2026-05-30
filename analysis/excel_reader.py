import pandas as pd
import io

def load_excel(file_obj):
    filename = getattr(file_obj, "name", str(file_obj))
    if filename.lower().endswith(".csv"):
        return _clean_df(pd.read_csv(file_obj)), []
    raw   = file_obj.read()
    xl    = pd.ExcelFile(io.BytesIO(raw))
    df    = pd.read_excel(io.BytesIO(raw), sheet_name=0)
    return _clean_df(df), xl.sheet_names

def _clean_df(df):
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df.reset_index(drop=True)

def get_column_summary(df):
    lines = [f"Dataset: {len(df)} rows, {len(df.columns)} columns:"]
    for col in df.columns:
        sample = df[col].dropna().head(3).tolist()
        lines.append(f"  - '{col}' ({df[col].dtype}): e.g. {sample}")
    return "\n".join(lines)

def get_quick_stats(df):
    numeric   = df.select_dtypes(include="number").columns.tolist()
    categoric = df.select_dtypes(include="object").columns.tolist()
    return {
        "rows":            len(df),
        "columns":         len(df.columns),
        "numeric_cols":    numeric,
        "categoric_cols":  categoric,
        "missing_pct":     round(df.isnull().mean().mean() * 100, 1),
        "numeric_summary": df[numeric].describe().round(2).to_dict() if numeric else {},
        "top_categories":  {
            col: df[col].value_counts().head(5).to_dict()
            for col in categoric[:4]
        },
    }
