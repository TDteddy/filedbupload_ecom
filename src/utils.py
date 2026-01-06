"""
Utility functions for data processing.
Includes column detection, data transformation, and mapping helpers.
"""

import pandas as pd


def get_matching_column(filename):
    """
    Determine which column to use for SKU matching based on filename.

    Args:
        filename: Name of the file being processed

    Returns:
        str: Column name to use for matching

    Raises:
        ValueError: If filename doesn't match any known pattern
    """
    lower = filename.lower()

    if "쿠팡_1p_전체" in lower:
        return "벤더아이템 ID"
    elif "쿠팡_2p_전체" in lower:
        return "옵션 ID"
    elif "쿠팡_매출성장광고" in lower:
        return "광고집행 옵션ID"
    elif "쿠팡_첫구매광고" in lower:
        return "광고집행 옵션 ID"
    elif "네이버_광고_대용량" in lower:
        return "스마트스토어 상품ID"
    elif "네이버_광고_보고서" in lower:
        return "소재"
    elif "네이버_오가닉" in lower:
        return "상품ID"
    elif "네이버기타" in lower:
        return "상품ID"
    elif "카페24" in lower:
        return "상품코드"
    else:
        raise ValueError(f"⚠️ 파일명에서 비교 컬럼을 판단할 수 없습니다: {filename}")


def get_target_table_name(filename):
    """
    Determine target database table based on filename.

    Args:
        filename: Name of the file being processed

    Returns:
        str or None: Table name, or None for special cases (e.g., Naver organic)

    Raises:
        ValueError: If filename doesn't match any known pattern
    """
    lower = filename.lower()

    if "쿠팡_1p_전체" in lower:
        return "sales_report_coupang_1p"
    elif "쿠팡_2p_전체" in lower:
        return "sales_report_coupang_2p"
    elif "쿠팡_매출성장광고" in lower:
        return "ad_report_coupang_by_growth"
    elif "쿠팡_첫구매광고" in lower:
        return "ad_report_coupang_by_firstbuy"
    elif "네이버_광고_대용량" in lower:
        return "ad_ID_daily_update_naver"
    elif "네이버_광고_보고서" in lower:
        return "ad_report_naver_summary"
    elif "네이버기타" in lower:
        return "sales_report_naver_etc"
    elif "네이버_오가닉" in lower:
        return None  # Special handling required
    elif "카페24" in lower:
        return "sales_report_cafe24"
    else:
        raise ValueError(f"⚠️ 파일명에서 저장할 테이블을 판단할 수 없습니다: {filename}")


def convert_percent_string_to_float(value):
    """
    Convert percentage string to float.

    Args:
        value: Value to convert (can be string with % or numeric)

    Returns:
        float or None: Converted value, or None if conversion fails
    """
    try:
        if isinstance(value, str) and "%" in value:
            return float(value.replace("%", "").strip()) / 100
        return float(value)
    except:
        return None


def normalize_numeric_columns(df, column_list=None):
    """
    Normalize numeric columns by removing commas and converting to numeric.

    Args:
        df: DataFrame to process
        column_list: List of columns to process, or None to auto-detect

    Returns:
        DataFrame: Processed dataframe
    """
    if column_list is None:
        # Auto-detect columns with Sales, Qty, Count, Cost in name
        column_list = [col for col in df.columns
                      if any(keyword in col for keyword in ["Sales", "Qty", "Count", "Cost"])]

    for col in column_list:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", "").str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def normalize_ratio_columns(df, column_list=None):
    """
    Normalize ratio/percentage columns.

    Args:
        df: DataFrame to process
        column_list: List of columns to process, or None to auto-detect

    Returns:
        DataFrame: Processed dataframe
    """
    if column_list is None:
        # Auto-detect columns with Ratio or ratio in name
        column_list = [col for col in df.columns
                      if "Ratio" in col or "ratio" in col or "ROAS" in col or "CVR" in col]

    for col in column_list:
        if col in df.columns:
            df[col] = df[col].apply(convert_percent_string_to_float)

    return df


def normalize_date_column(df, date_column="Date"):
    """
    Normalize date column to datetime format.

    Args:
        df: DataFrame to process
        date_column: Name of the date column

    Returns:
        DataFrame: Processed dataframe
    """
    if date_column in df.columns:
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')

    return df


def load_naver_master_map(engine):
    """
    Load Naver master mapping from database.

    Args:
        engine: SQLAlchemy engine

    Returns:
        dict: Mapping of ad item IDs to master IDs
    """
    try:
        df_naver_master = pd.read_sql(
            "SELECT ID_ad_item_at_ad_ID_daily_update_naver, ID_master FROM ad_ID_daily_update_naver",
            con=engine
        )
        return dict(zip(
            df_naver_master["ID_ad_item_at_ad_ID_daily_update_naver"].astype(str),
            df_naver_master["ID_master"]
        ))
    except Exception as e:
        print(f"❌ 네이버 마스터 테이블 로딩 실패: {e}")
        return {}


def load_sku_mappings(session):
    """
    Load SKU mapping tables from database.

    Args:
        session: SQLAlchemy session

    Returns:
        tuple: (sku_primary_map, sku_by_sku_id, sku_naver_map, sku_cafe24_map, auto_map)
    """
    from models import SKU_master, coupang_1p_auto_created_vender_ID

    print("🔄 SKU_master & 보조 테이블 불러오는 중...")

    # Load all SKU master records
    sku_all = session.query(SKU_master).all()

    # Create mappings
    sku_primary_map = {
        str(s.ID_option_vendor_coupang_at_SKU_master): s.ID_master
        for s in sku_all
    }

    sku_by_sku_id = {
        str(s.ID_product_sku_coupang_at_SKU_master): s.ID_master
        for s in sku_all
    }

    sku_naver_map = {
        str(s.ID_product_naver_at_SKU_master): s.ID_master
        for s in sku_all
    }

    sku_cafe24_map = {
        str(s.ID_product_cafe24_at_SKU_master).strip(): s.ID_master
        for s in sku_all
        if s.ID_product_cafe24_at_SKU_master
    }

    # Strip whitespace from all keys
    sku_naver_map = {k.strip(): v for k, v in sku_naver_map.items()}
    sku_by_sku_id = {k.strip(): v for k, v in sku_by_sku_id.items()}
    sku_primary_map = {k.strip(): v for k, v in sku_primary_map.items()}

    # Load auto-created vendor IDs (optional legacy table)
    auto_map = {}
    try:
        auto_created = session.query(coupang_1p_auto_created_vender_ID).all()
        auto_map = {
            str(a.ID_option_vendor_coupang_at_coupang_1p_auto_created_vender_ID):
            str(a.ID_product_sku_coupang_at_coupang_1p_auto_created_vender_ID)
            for a in auto_created
        }
        if auto_map:
            print(f"   ℹ️  Auto-created vendor ID 매핑 {len(auto_map)}개 로드됨")
    except Exception as e:
        print(f"   ⚠️  Auto-created vendor ID 테이블 없음 (선택사항, 무시해도 됨)")
        auto_map = {}

    print("✅ 매핑 테이블 준비 완료")

    return sku_primary_map, sku_by_sku_id, sku_naver_map, sku_cafe24_map, auto_map


def read_file(filepath):
    """
    Read Excel or CSV file into DataFrame.

    Args:
        filepath: Path to the file

    Returns:
        DataFrame: Loaded data

    Raises:
        ValueError: If file format is not supported
    """
    import os

    ext = os.path.splitext(filepath)[-1].lower()

    if ext == ".xlsx":
        return pd.read_excel(filepath)
    elif ext == ".csv":
        try:
            return pd.read_csv(filepath, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(filepath, encoding="ansi")
    else:
        raise ValueError(f"⚠️ 지원되지 않는 파일 형식: {filepath}")


def save_output_file(df, original_filepath, prefix="output_"):
    """
    Save processed DataFrame to output file.

    Args:
        df: DataFrame to save
        original_filepath: Original file path
        prefix: Prefix for output filename
    """
    import os

    filename = os.path.basename(original_filepath)
    ext = os.path.splitext(original_filepath)[-1].lower()
    output_path = os.path.join(os.path.dirname(original_filepath), f"{prefix}{filename}")

    if ext == ".xlsx":
        df.to_excel(output_path, index=False)
    elif ext == ".csv":
        df.to_csv(output_path, index=False)

    print(f"📁 저장 완료: {output_path}")
    return output_path


def save_unmatched_file(df_unmatched, original_filepath):
    """
    Save unmatched records to a separate file.

    Args:
        df_unmatched: DataFrame with unmatched records
        original_filepath: Original file path
    """
    import os

    if df_unmatched.empty:
        return

    filename = os.path.basename(original_filepath)
    ext = os.path.splitext(original_filepath)[-1].lower()
    unmatched_path = os.path.join(
        os.path.dirname(original_filepath),
        f"unmatched_{filename}"
    )

    if ext == ".xlsx":
        df_unmatched.to_excel(unmatched_path, index=False)
    else:
        df_unmatched.to_csv(unmatched_path, index=False)

    print(f"⚠️ 매칭 실패 {len(df_unmatched)}건 → {unmatched_path} 저장됨")
    return unmatched_path
