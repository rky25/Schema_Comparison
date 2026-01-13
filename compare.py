import pandas as pd

# ---------------------------------------
# COLUMN AUTO-MAPPING
# Standardizes common column name variations
# ---------------------------------------
COLUMN_ALIASES = {
    "schema_name": ["schema_name", "table_schema", "schema"],
    "table_name": ["table_name", "table name", "table", "tablename"],
    "column_name": ["column_name", "column", "columnname", "column name"],
    "data_type": ["data_type", "datatype", "data type", "type"],
    "max_length": ["max_length", "length", "lenth", "char_length", "character_maximum_length"],
    "is_nullable": ["is_nullable", "nullable", "is null", "nullability", "null"],
    "precision": ["precision", "numeric_precision"],
    "scale": ["scale", "numeric_scale"],
    "default_value": ["default_value", "column_default", "default"],
    "primary_key": ["primary_key", "is_primary_key", "pk"],
    "identity": ["identity", "is_identity", "auto_increment"],
}

# These columns are essential for comparison (at minimum)
REQUIRED_COLUMNS = ["table_name", "column_name"]

# These columns will be compared if present in both files
COMPARISON_COLUMNS = ["data_type", "max_length", "is_nullable", "precision", "scale", "default_value"]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to standard format using aliases."""
    df.columns = df.columns.str.strip().str.lower()
    rename_map = {}

    for standard, aliases in COLUMN_ALIASES.items():
        for col in df.columns:
            if col in aliases:
                rename_map[col] = standard

    return df.rename(columns=rename_map)


def get_common_columns(source: pd.DataFrame, target: pd.DataFrame) -> list:
    """Get columns that exist in both source and target (excluding key columns)."""
    source_cols = set(source.columns)
    target_cols = set(target.columns)
    common = source_cols & target_cols
    
    # Remove key columns from comparison columns (they're used for matching)
    key_cols = {"table_name", "column_name", "schema_name"}
    comparison_cols = common - key_cols
    
    return sorted(list(comparison_cols))


# ---------------------------------------
# MAIN COMPARISON FUNCTION
# ---------------------------------------
def compare_schemas(source: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    """
    Compare two schema DataFrames.
    Compares all common columns between the two files.
    Outputs in fixed format: table_name, column_in_source, column_in_target, 
    source_datatype, target_datatype, source_length, target_length, comment
    """
    source = normalize_columns(source.copy())
    target = normalize_columns(target.copy())

    # Add default schema if not present
    for df in (source, target):
        if "schema_name" not in df.columns:
            df["schema_name"] = "default_schema"

    # Check required columns
    for col in REQUIRED_COLUMNS:
        if col not in source.columns:
            raise ValueError(f"SOURCE file missing required column: {col}")
        if col not in target.columns:
            raise ValueError(f"TARGET file missing required column: {col}")

    # Get columns to compare (common between both files)
    compare_cols = get_common_columns(source, target)
    
    print(f"📊 Comparing columns: {compare_cols}")
    
    # Convert all relevant columns to string for comparison
    all_cols = REQUIRED_COLUMNS + compare_cols
    for df in (source, target):
        for col in all_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

    results = []
    all_tables = sorted(set(source["table_name"]) | set(target["table_name"]))

    for table in all_tables:
        source_tbl = source[source["table_name"] == table]
        target_tbl = target[target["table_name"] == table]

        if source_tbl.empty:
            results.append(_row(table, "", "", "", "", "", "", "table missing in SOURCE"))
            continue

        if target_tbl.empty:
            results.append(_row(table, "", "", "", "", "", "", "table missing in TARGET"))
            continue

        # Get all columns from both tables
        source_map = {c.lower(): c for c in source_tbl["column_name"]}
        target_map = {c.lower(): c for c in target_tbl["column_name"]}
        all_cols_list = sorted(set(source_map) | set(target_map))

        for lc in all_cols_list:
            source_col = source_map.get(lc)
            target_col = target_map.get(lc)

            if not source_col:
                results.append(_row(table, "", target_col, "", "", "", "", "column missing in SOURCE"))
                continue

            if not target_col:
                results.append(_row(table, source_col, "", "", "", "", "", "column missing in TARGET"))
                continue

            # Column name case difference
            if source_col != target_col:
                results.append(_row(table, source_col, target_col, "", "", "", "", "column rename required"))
                continue

            # Get actual row data
            source_row = source_tbl[source_tbl["column_name"].str.lower() == lc].iloc[0]
            target_row = target_tbl[target_tbl["column_name"].str.lower() == lc].iloc[0]

            # Get values with fallbacks
            source_dtype = source_row.get("data_type", "") if "data_type" in source_tbl.columns else ""
            target_dtype = target_row.get("data_type", "") if "data_type" in target_tbl.columns else ""
            source_len = source_row.get("max_length", "") if "max_length" in source_tbl.columns else ""
            target_len = target_row.get("max_length", "") if "max_length" in target_tbl.columns else ""

            # Normalize empty/nan values
            source_dtype = "" if str(source_dtype).lower() in ["nan", "none"] else str(source_dtype)
            target_dtype = "" if str(target_dtype).lower() in ["nan", "none"] else str(target_dtype)
            source_len = "" if str(source_len).lower() in ["nan", "none"] else str(source_len)
            target_len = "" if str(target_len).lower() in ["nan", "none"] else str(target_len)

            # Compare ALL common columns and collect differences
            differences = []
            
            # Check data_type
            if source_dtype.lower() != target_dtype.lower() and (source_dtype or target_dtype):
                differences.append("datatype differs")

            # Check max_length
            if source_len != target_len and (source_len or target_len):
                differences.append("length differs")

            # Check is_nullable if present
            if "is_nullable" in compare_cols:
                source_null = str(source_row.get("is_nullable", "")).strip().lower()
                target_null = str(target_row.get("is_nullable", "")).strip().lower()
                source_null = "" if source_null in ["nan", "none"] else source_null
                target_null = "" if target_null in ["nan", "none"] else target_null
                if source_null != target_null and (source_null or target_null):
                    differences.append("nullable differs")

            # Check precision if present
            if "precision" in compare_cols:
                source_prec = str(source_row.get("precision", "")).strip()
                target_prec = str(target_row.get("precision", "")).strip()
                source_prec = "" if source_prec.lower() in ["nan", "none"] else source_prec
                target_prec = "" if target_prec.lower() in ["nan", "none"] else target_prec
                if source_prec != target_prec and (source_prec or target_prec):
                    differences.append("precision differs")

            # Check scale if present
            if "scale" in compare_cols:
                source_scale = str(source_row.get("scale", "")).strip()
                target_scale = str(target_row.get("scale", "")).strip()
                source_scale = "" if source_scale.lower() in ["nan", "none"] else source_scale
                target_scale = "" if target_scale.lower() in ["nan", "none"] else target_scale
                if source_scale != target_scale and (source_scale or target_scale):
                    differences.append("scale differs")

            # Add result if there are differences
            if differences:
                comment = ", ".join(differences)
                results.append(_row(table, source_col, target_col, source_dtype, target_dtype, source_len, target_len, comment))

    return pd.DataFrame(
        results,
        columns=[
            "table_name",
            "column_in_source",
            "column_in_target",
            "source_datatype",
            "target_datatype",
            "source_length",
            "target_length",
            "comment"
        ]
    )


# ---------------------------------------
# HELPER
# ---------------------------------------
def _row(tbl, civ, cis, vdt, sdt, vlen, slen, comment):
    return {
        "table_name": tbl,
        "column_in_source": civ,
        "column_in_target": cis,
        "source_datatype": vdt,
        "target_datatype": sdt,
        "source_length": vlen,
        "target_length": slen,
        "comment": comment
    }


# ---------------------------------------
# BUILD AI-READY STRUCTURED JSON
# Compatible with the new dynamic format
# ---------------------------------------
def build_schema_changes_from_df(df: pd.DataFrame, direction: str) -> list:
    changes = []

    for _, row in df.iterrows():
        comment = str(row.get("comment", "")).lower()
        table = row["table_name"]
        source_col = row.get("column_in_source", "")
        target_col = row.get("column_in_target", "")

        if "column rename required" in comment or "rename" in comment:
            frm, to = (
                (target_col, source_col)
                if direction == "target_to_source"
                else (source_col, target_col)
            )
            changes.append({
                "change_type": "column_rename",
                "table": table,
                "from": frm,
                "to": to,
                "direction": direction
            })

        elif "column missing" in comment or "missing" in comment:
            if "source" in comment.lower():
                changes.append({
                    "change_type": "add_column",
                    "table": table,
                    "column": target_col,
                    "target": "source" if direction == "target_to_source" else "target",
                    "direction": direction
                })
            else:
                changes.append({
                    "change_type": "add_column",
                    "table": table,
                    "column": source_col,
                    "target": "target" if direction == "target_to_source" else "source",
                    "direction": direction
                })

        elif "differs" in comment:
            # Extract what differs from comment
            diff_parts = comment.replace("differs:", "").strip().split(",")
            
            for diff in diff_parts:
                diff = diff.strip()
                source_val = row.get(f"source_{diff}", "")
                target_val = row.get(f"target_{diff}", "")
                
                changes.append({
                    "change_type": f"{diff}_mismatch",
                    "table": table,
                    "column": source_col or target_col,
                    "from": target_val if direction == "target_to_source" else source_val,
                    "to": source_val if direction == "target_to_source" else target_val,
                    "direction": direction
                })


        elif "table missing" in comment:
            # Skip missing tables - we don't have column information to create table scripts
            # The AI cannot generate a CREATE TABLE script without knowing the fields
            print(f"⚠️ Skipping missing table '{table}' - no column information available")
            continue

    return changes
