"""
File processors for different e-commerce platforms.
Handles data transformation, SKU matching, and database uploads.
"""

import os
import pandas as pd
from config.mappings import (
    COLUMN_MAPPING_1P,
    COLUMN_MAPPING_2P,
    COLUMN_MAPPING_AD,
    COLUMN_MAPPING_AD_FIRSTBUY,
    COLUMN_MAPPING_SALE_OWNED,
    COLUMN_MAPPING_NAVER_MASTER,
    COLUMN_MAPPING_NAVER_REPORT,
    COLUMN_MAPPING_NAVER_ORGANIC_PURCHASE,
    COLUMN_MAPPING_NAVER_ORGANIC_CLICK,
    COLUMN_MAPPING_SALES_REPORT_NAVER_ETC,
)
from src.utils import (
    get_matching_column,
    get_target_table_name,
    normalize_numeric_columns,
    normalize_ratio_columns,
    normalize_date_column,
    read_file,
    save_output_file,
    save_unmatched_file,
    load_naver_master_map,
)


class FileProcessor:
    """Main file processor for e-commerce data files."""

    def __init__(self, engine, sku_mappings, db_manager=None, session=None, all_only_mode=False):
        """
        Initialize processor with database engine and SKU mappings.

        Args:
            engine: SQLAlchemy engine
            sku_mappings: Tuple of (sku_primary_map, sku_by_sku_id, sku_naver_map, sku_cafe24_map, auto_map)
            db_manager: DatabaseManager instance (for SKU updates)
            session: SQLAlchemy session
            all_only_mode: If True, 쿠팡_2p_전체 files upload to ALL table only (no matching)
        """
        self.engine = engine
        self.sku_primary_map, self.sku_by_sku_id, self.sku_naver_map, self.sku_cafe24_map, self.auto_map = sku_mappings
        self.db_manager = db_manager
        self.session = session
        self.all_only_mode = all_only_mode

        # Initialize GPT analyzer and SKU generator
        try:
            from src.gpt_analyzer import CoupangProductAnalyzer
            from src.sku_generator import SKUGenerator
            self.gpt_analyzer = CoupangProductAnalyzer()
            self.sku_generator = SKUGenerator(session) if session else None
            print("✅ GPT 자동 매칭 시스템 활성화")
        except Exception as e:
            print(f"⚠️ GPT 시스템 초기화 실패: {e}")
            self.gpt_analyzer = None
            self.sku_generator = None

    def _generate_cost_update_report(self, newly_created, filename):
        """
        Generate cost update report for newly created SKUs.

        Args:
            newly_created: List of newly created SKU dictionaries
            filename: Original filename for report naming
        """
        from datetime import datetime

        # Build report message
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("⚠️  신규 SKU 원가 업데이트 필요")
        report_lines.append("=" * 70)
        report_lines.append("")
        report_lines.append(f"파일: {filename}")
        report_lines.append(f"처리일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"신규 생성 SKU: {len(newly_created)}건")
        report_lines.append("")
        report_lines.append("다음 SKU들이 자동 생성되었으나 원가 정보가 없습니다.")
        report_lines.append("담당자에게 아래 내용을 전달하여 SKU_master 테이블 원가 업데이트를 요청하세요.")
        report_lines.append("")
        report_lines.append("-" * 70)
        report_lines.append("신규 생성된 SKU 목록:")
        report_lines.append("-" * 70)
        report_lines.append("")

        for i, item in enumerate(newly_created, 1):
            report_lines.append(f"{i}. ID: {item['new_master_id']}")
            report_lines.append(f"   상품명: {item['product_name']}")
            report_lines.append(f"   분류: {item['case_name']}")
            if item['base_master_id']:
                report_lines.append(f"   기반 ID: {item['base_master_id']}")
            report_lines.append(f"   현재 원가: {item['cost']}원 ⚠️ 업데이트 필요")
            report_lines.append("")

        report_lines.append("-" * 70)
        report_lines.append("📋 SQL 업데이트 쿼리 예시:")
        report_lines.append("-" * 70)
        report_lines.append("")

        for item in newly_created:
            report_lines.append(f"UPDATE SKU_master SET Cost_product_at_SKU_master = [실제원가] WHERE ID_master = '{item['new_master_id']}';")

        report_lines.append("")
        report_lines.append("=" * 70)
        report_lines.append("⚠️ 위 내용을 담당자에게 전달하여 원가 업데이트를 요청해주세요.")
        report_lines.append("=" * 70)

        # Print to console
        report_text = "\n".join(report_lines)
        print("\n" + report_text)

        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"원가_업데이트_필요_{timestamp}.txt"

        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n📄 보고서 저장됨: {report_filename}")
            print("   → 이 파일을 담당자에게 전달하여 원가 업데이트를 요청하세요.")
        except Exception as e:
            print(f"⚠️ 보고서 파일 저장 실패: {e}")

    def upload_coupang_2p_all(self, df_original, table_name="sales_report_coupang_2p_all"):
        """
        Upload entire Coupang 2P data including unmatched records.

        Args:
            df_original: Original DataFrame
            table_name: Target table name
        """
        df_all = df_original.copy()

        # Rename columns
        df_all.rename(columns=COLUMN_MAPPING_2P, inplace=True)

        # Normalize numeric columns
        df_all = normalize_numeric_columns(df_all)

        # Normalize ratio columns
        df_all = normalize_ratio_columns(df_all)

        # Normalize date
        df_all = normalize_date_column(df_all)

        # Keep only valid columns
        valid_columns = ["ID_master"] + list(COLUMN_MAPPING_2P.values())
        df_all = df_all[[c for c in df_all.columns if c in valid_columns]]

        # Upload to database
        df_all.to_sql(table_name, con=self.engine, if_exists="append", index=False)
        print(f"🛠 2P 원본 전체 저장 완료 ({len(df_all)}건): {table_name}")

    def process_coupang_2p_all_only(self, filepath, df, compare_column, table_name):
        """
        Process Coupang 2P file for all table only (no matching, no GPT).
        Directly uploads to sales_report_coupang_2p_all without SKU matching.

        Args:
            filepath: Path to file
            df: DataFrame
            compare_column: Column name for comparison (not used, for compatibility)
            table_name: Target table name (not used, always uses sales_report_coupang_2p_all)
        """
        filename = os.path.basename(filepath)
        print(f"\n📦 쿠팡 2P ALL 전용 처리 시작: {filename}")
        print(f"ℹ️ SKU 매칭 없이 sales_report_coupang_2p_all에만 업로드합니다")

        # Upload to _all table only (no matching required)
        self.upload_coupang_2p_all(df.copy())

        print(f"✅ 처리 완료: {filename}")

    def process_naver_organic(self, filepath):
        """Process Naver organic Excel file with multiple sheets."""
        filename = os.path.basename(filepath)
        sheet_click = "통계_마케팅분석_상품노출성과"
        sheet_purchase = "통계_판매분석_상품_검색채널"

        def load_organic_sheet(sheet_name):
            """Load and clean organic sheet data."""
            df = pd.read_excel(filepath, sheet_name=sheet_name)

            if any("Unnamed" in str(col) for col in df.columns):
                print(f"⚠️ 병합 헤더 감지됨: {sheet_name} → 헤더 재설정 중")
                df = pd.read_excel(filepath, sheet_name=sheet_name, header=[0, 1])
                df.columns = [' '.join(col).strip() for col in df.columns.values]

            # Remove rows with all "전체" values
            df = df[~df.apply(lambda row: row.astype(str).str.contains("전체").any(), axis=1)]
            return df

        # Process click sheet
        df_click = load_organic_sheet(sheet_click)
        df_click["상품ID"] = df_click["상품ID"].apply(
            lambda x: str(int(float(x))) if pd.notnull(x) else ''
        )
        df_click["ID_master"] = df_click["상품ID"].map(self.sku_naver_map)

        # Handle missing date
        if "날짜" not in df_click.columns or df_click["날짜"].isnull().all():
            default_date = input(f"📅 파일 '{filename}'의 날짜가 없습니다. 적용할 날짜를 YYYY-MM-DD 형식으로 입력하세요: ")
            df_click["날짜"] = default_date

        # Filter matched records
        df_click = df_click[df_click["ID_master"].notnull()]
        df_click.rename(columns=COLUMN_MAPPING_NAVER_ORGANIC_CLICK, inplace=True)

        # Save to database
        df_click.to_sql("keyword_click_report_naver_organic", con=self.engine, if_exists='append', index=False)
        print(f"🛠 DB 저장 완료 ({len(df_click)}건): keyword_click_report_naver_organic")

        # Save output files
        click_output_path = os.path.join(
            os.path.dirname(filepath),
            f"output_click_{filename.replace('.xlsx', '.csv')}"
        )
        df_click.to_csv(click_output_path, index=False)
        print(f"📁 클릭 결과 저장 완료: {click_output_path}")

        # Process purchase sheet
        df_purchase = load_organic_sheet(sheet_purchase)
        df_purchase["상품ID"] = df_purchase["상품ID"].apply(
            lambda x: str(int(float(x))) if pd.notnull(x) else ''
        )
        df_purchase["ID_master"] = df_purchase["상품ID"].map(self.sku_naver_map)

        # Use same date as click sheet
        if "날짜" not in df_purchase.columns or df_purchase["날짜"].isnull().all():
            df_purchase["날짜"] = default_date

        # Filter matched records
        df_purchase = df_purchase[df_purchase["ID_master"].notnull()]
        df_purchase.rename(columns=COLUMN_MAPPING_NAVER_ORGANIC_PURCHASE, inplace=True)

        # Save to database
        df_purchase.to_sql("keyword_purchase_report_naver_organic", con=self.engine, if_exists='append', index=False)
        print(f"🛠 DB 저장 완료 ({len(df_purchase)}건): keyword_purchase_report_naver_organic")

        # Save output files
        purchase_output_path = os.path.join(
            os.path.dirname(filepath),
            f"output_purchase_{filename.replace('.xlsx', '.csv')}"
        )
        df_purchase.to_csv(purchase_output_path, index=False)
        print(f"📁 구매 결과 저장 완료: {purchase_output_path}")

    def process_naver_master(self, filepath, df, compare_column, table_name):
        """Process Naver master (대용량) file."""
        df[compare_column] = df[compare_column].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

        print("📦 sku_naver_map 키 샘플 (5개):", list(self.sku_naver_map.keys())[:5])
        print(f"🔍 매핑 시도 대상 컬럼 샘플 (상위 5개):\n{df[compare_column].head()}")

        df["ID_master"] = df[compare_column].map(self.sku_naver_map)

        unmatched_count = df["ID_master"].isnull().sum()
        matched_count = len(df) - unmatched_count
        print(f"🔄 매핑 결과: 매칭 {matched_count}건 / 실패 {unmatched_count}건")

        # Filter matched records
        df_matched = df[df["ID_master"].notnull()].copy()
        df_matched.rename(columns=COLUMN_MAPPING_NAVER_MASTER, inplace=True)

        # Save to database
        df_matched.to_sql(table_name, con=self.engine, if_exists='append', index=False)
        print(f"🛠 DB 저장 완료 ({len(df_matched)}건): {table_name}")

        # Save output and unmatched files
        save_output_file(df, filepath)
        save_unmatched_file(df[df["ID_master"].isnull()], filepath)

    def process_naver_report(self, filepath, df, compare_column, table_name):
        """Process Naver ad report file."""
        material_to_master = load_naver_master_map(self.engine)

        df[compare_column] = (
            df[compare_column].astype(str)
            .str.replace(r"\(삭제\)", "", regex=True)
            .str.strip()
        )

        df["ID_master"] = df[compare_column].map(material_to_master)

        # Filter matched records
        df_matched = df[df["ID_master"].notnull()].copy()
        df_matched.rename(columns=COLUMN_MAPPING_NAVER_REPORT, inplace=True)

        # Normalize columns
        df_matched = normalize_ratio_columns(df_matched)
        df_matched = normalize_numeric_columns(df_matched)
        df_matched = normalize_date_column(df_matched)

        # Save to database
        df_matched.to_sql(table_name, con=self.engine, if_exists='append', index=False)
        print(f"🛠 DB 저장 완료 ({len(df_matched)}건): {table_name}")

        # Save output and unmatched files
        save_output_file(df, filepath)
        save_unmatched_file(df[df["ID_master"].isnull()], filepath)

    def process_naver_etc(self, filepath, df, compare_column, table_name):
        """Process Naver etc sales report file."""
        filename = os.path.basename(filepath)

        df[compare_column] = df[compare_column].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        df["ID_master"] = df[compare_column].map(self.sku_naver_map)

        # Handle merged headers
        if any("Unnamed" in str(col) for col in df.columns):
            print(f"⚠️ 병합 헤더 감지됨: {filename} → 헤더 재설정 중")
            df = pd.read_excel(filepath, header=[0, 1])
            df.columns = [' '.join(col).strip() for col in df.columns.values]

        # Remove "전체" rows
        df = df[~df.apply(lambda row: row.astype(str).str.contains("전체").any(), axis=1)]
        df = df[df[compare_column].notnull()]

        # Handle missing date
        if "날짜" not in df.columns or df["날짜"].isnull().all():
            default_date = input(f"📅 파일 '{filename}'의 날짜가 없습니다. 적용할 날짜를 YYYY-MM-DD 형식으로 입력하세요: ")
            df["날짜"] = default_date

        # Filter matched records
        df_matched = df[df["ID_master"].notnull()].copy()
        df_matched.rename(columns=COLUMN_MAPPING_SALES_REPORT_NAVER_ETC, inplace=True)

        # Normalize columns
        df_matched = normalize_ratio_columns(df_matched)
        df_matched = normalize_numeric_columns(df_matched)
        df_matched = normalize_date_column(df_matched)

        # Save to database
        df_matched.to_sql(table_name, con=self.engine, if_exists='append', index=False)
        print(f"🛠 DB 저장 완료 ({len(df_matched)}건): {table_name}")

        # Save output and unmatched files
        save_output_file(df, filepath)
        save_unmatched_file(df[df["ID_master"].isnull()], filepath)

    def process_cafe24(self, filepath, df, compare_column, table_name):
        """Process Cafe24 sales file."""
        df[compare_column] = df[compare_column].astype(str).str.strip()
        df["ID_master"] = df[compare_column].map(self.sku_cafe24_map)

        # Filter matched records
        df_matched = df[df["ID_master"].notnull()].copy()
        df_matched.rename(columns=COLUMN_MAPPING_SALE_OWNED, inplace=True)

        # Add missing column
        df_matched["Count_sales_by_category_at_sales_report_cafe24"] = 0

        # Normalize columns
        df_matched = normalize_ratio_columns(df_matched)
        df_matched = normalize_numeric_columns(df_matched)
        df_matched = normalize_date_column(df_matched)

        # Save to database
        df_matched.to_sql(table_name, con=self.engine, if_exists='append', index=False)
        print(f"🛠 DB 저장 완료 ({len(df_matched)}건): {table_name}")

        # Save unmatched file
        save_unmatched_file(df[df["ID_master"].isnull()], filepath)

    def process_coupang_firstbuy(self, filepath, df, compare_column, table_name):
        """Process Coupang first buy ad file."""
        df[compare_column] = df[compare_column].astype(str).str.strip()
        df["ID_master"] = df[compare_column].map(self.sku_primary_map)

        # Filter matched records
        df_matched = df[df["ID_master"].notnull()].copy()
        df_matched.rename(columns=COLUMN_MAPPING_AD_FIRSTBUY, inplace=True)

        # Normalize columns
        df_matched = normalize_ratio_columns(df_matched)
        df_matched = normalize_numeric_columns(df_matched)
        df_matched = normalize_date_column(df_matched)

        # Save to database
        df_matched.to_sql(table_name, con=self.engine, if_exists='append', index=False)
        print(f"🛠 DB 저장 완료 ({len(df_matched)}건): {table_name}")

        # Save unmatched file
        save_unmatched_file(df[df["ID_master"].isnull()], filepath)

    def process_coupang_common(self, filepath, df, compare_column, table_name):
        """Process common Coupang files (1P, 2P, Growth Ad)."""
        # Normalize IDs
        df[compare_column] = df[compare_column].apply(
            lambda x: str(int(float(x))) if pd.notnull(x) and str(x).strip() != '' else ''
        )

        # Match IDs
        matched_ids = []
        for value in df[compare_column]:
            value_str = str(value).strip()
            id_master = self.sku_primary_map.get(str(value_str))

            if not id_master:
                # Try auto-created vendor ID mapping
                sku_id = self.auto_map.get(str(value_str))
                if sku_id:
                    id_master = self.sku_by_sku_id.get(str(sku_id))
                    if id_master:
                        print(f"✅ 최종 매핑 성공: 옵션ID {value_str} → SKU ID {sku_id} → ID_master {id_master}")

            matched_ids.append(id_master)

        # Add ID_master column
        if "ID_master" not in df.columns:
            df.insert(0, "ID_master", matched_ids)
        else:
            df["ID_master"] = matched_ids

        # Save backup output file
        save_output_file(df, filepath)

        # Upload 2P all data if applicable
        if table_name == "sales_report_coupang_2p":
            self.upload_coupang_2p_all(df)

        # Select column mapping
        if table_name == "sales_report_coupang_1p":
            header_mapping = COLUMN_MAPPING_1P
        elif table_name == "sales_report_coupang_2p":
            header_mapping = COLUMN_MAPPING_2P
        elif table_name == "ad_report_coupang_by_growth":
            header_mapping = COLUMN_MAPPING_AD
        else:
            raise ValueError("❌ 테이블 이름이 잘못되었습니다.")

        # Filter matched records and rename columns
        df_matched = df[df["ID_master"].notnull()].copy()
        df_matched.rename(columns=header_mapping, inplace=True)

        # Normalize columns
        df_matched = normalize_numeric_columns(df_matched)
        df_matched = normalize_ratio_columns(df_matched)

        # Keep only valid columns
        valid_columns = ["ID_master"] + list(header_mapping.values())
        df_matched = df_matched[[col for col in df_matched.columns if col in valid_columns]]

        # Normalize date
        df_matched = normalize_date_column(df_matched)

        # Save to database
        if not df_matched.empty:
            df_matched.to_sql(table_name, con=self.engine, if_exists='append', index=False)
            print(f"🛠 DB 저장 완료 ({len(df_matched)}건): {table_name}")
        else:
            print("ℹ️ 저장할 매칭된 데이터가 없습니다.")

        # Save unmatched file
        save_unmatched_file(df[df["ID_master"].isnull()], filepath)

    def process_file(self, filepath):
        """
        Main file processing dispatcher.

        Args:
            filepath: Path to file to process
        """
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filepath)[-1].lower()
        print(f"\n▶ 처리 시작: {filename}")

        try:
            # Special handling for Naver organic Excel
            if "네이버_오가닉" in filename and ext == ".xlsx":
                self.process_naver_organic(filepath)
                return

            # Get processing parameters
            compare_column = get_matching_column(filename)
            table_name = get_target_table_name(filename)

            # Read file
            df = read_file(filepath)

            # Route to appropriate processor
            if "네이버_광고_대용량" in filename:
                self.process_naver_master(filepath, df, compare_column, table_name)
            elif "네이버_광고_보고서" in filename:
                self.process_naver_report(filepath, df, compare_column, table_name)
            elif "네이버기타" in filename:
                self.process_naver_etc(filepath, df, compare_column, table_name)
            elif "카페24" in filename:
                self.process_cafe24(filepath, df, compare_column, table_name)
            elif "쿠팡_첫구매광고" in filename:
                self.process_coupang_firstbuy(filepath, df, compare_column, table_name)
            elif "쿠팡_2p_전체" in filename.lower():
                # Coupang 2P processing
                if self.all_only_mode:
                    # ALL table only (no matching, direct upload)
                    self.process_coupang_2p_all_only(filepath, df, compare_column, table_name)
                else:
                    # GPT auto-matching + ALL table
                    self.process_coupang_2p_with_gpt(filepath, df, compare_column, table_name)
            else:
                # Common Coupang processing (1P, Growth Ad)
                self.process_coupang_common(filepath, df, compare_column, table_name)

        except Exception as e:
            print(f"❌ 처리 중 오류 발생: {e}")
            raise

    def process_coupang_2p_with_gpt(self, filepath, df, compare_column, table_name):
        """
        Process Coupang 2P file with GPT-based auto SKU matching.
        Unmatched products are analyzed by GPT and automatically added to SKU_master.
        """
        filename = os.path.basename(filepath)
        print(f"\n🤖 GPT 기반 쿠팡 2P 처리 시작: {filename}")

        # Normalize IDs
        df[compare_column] = df[compare_column].apply(
            lambda x: str(int(float(x))) if pd.notnull(x) and str(x).strip() != '' else ''
        )

        # 1차 매칭: 기존 SKU_master와 직접 매칭
        df["ID_master"] = df[compare_column].map(self.sku_primary_map)

        matched_count = df["ID_master"].notnull().sum()
        unmatched_count = df["ID_master"].isnull().sum()

        print(f"📊 1차 매칭 결과: 성공 {matched_count}건 / 실패 {unmatched_count}건")

        # Save backup output file
        save_output_file(df, filepath)

        # Upload 2P all data (including unmatched)
        self.upload_coupang_2p_all(df.copy())

        # Process unmatched records with GPT
        if unmatched_count > 0 and self.gpt_analyzer and self.sku_generator:
            print(f"\n🔍 GPT 분석 시작: {unmatched_count}건의 미매칭 상품")
            df_unmatched = df[df["ID_master"].isnull()].copy()

            # Get existing SKU data for GPT analysis
            from models import SKU_master
            existing_skus = self.session.query(SKU_master).all()
            existing_skus_list = [sku.to_dict() for sku in existing_skus]

            # Get all existing master IDs
            existing_master_ids = self.db_manager.get_all_master_ids()

            newly_created = []

            for idx, row in df_unmatched.iterrows():
                option_id = str(row[compare_column])
                if not option_id:
                    continue

                print(f"\n━━━ 처리 중 ({idx+1}/{len(df_unmatched)}): 옵션 ID {option_id} ━━━")

                # Prepare product info for GPT
                unmatched_product = {
                    'option_id': option_id,
                    'option_name': row.get('옵션명', ''),
                    'product_id': row.get('등록상품ID', ''),
                    'category': row.get('카테고리', ''),
                    'sales_type': row.get('판매방식', ''),
                }

                # GPT analysis
                try:
                    analysis_result = self.gpt_analyzer.analyze_product(
                        unmatched_product,
                        existing_skus_list
                    )

                    case_type = analysis_result['case_type']
                    base_master_id = analysis_result['base_master_id']
                    confidence = analysis_result['confidence']
                    reasoning = analysis_result['reasoning']

                    case_names = {
                        1: "개수변경 자동생성 (같은 패키지)",
                        2: "환불재판매",
                        3: "신규상품 (용량변경 포함)"
                    }

                    print(f"🎯 GPT 분석 결과:")
                    print(f"   케이스: {case_names.get(case_type, '알수없음')}")
                    print(f"   기초 ID: {base_master_id or 'N/A'}")
                    print(f"   확신도: {confidence:.2f}")
                    print(f"   근거: {reasoning}")

                    # Generate new master ID
                    new_master_id = self.sku_generator.generate_new_master_id(
                        case_type,
                        base_master_id,
                        existing_master_ids
                    )

                    print(f"🆔 새 ID_master 생성: {new_master_id}")

                    # Get base SKU data if needed
                    base_sku = None
                    if base_master_id:
                        base_sku = self.db_manager.get_sku_by_master_id(base_master_id)

                    # Generate SKU record
                    sku_record = self.sku_generator.generate_sku_record(
                        case_type,
                        new_master_id,
                        unmatched_product,
                        base_sku
                    )

                    # Insert into SKU_master
                    if self.db_manager.insert_sku_master(sku_record):
                        # Update DataFrame
                        df.loc[idx, "ID_master"] = new_master_id

                        # Add to existing master IDs
                        existing_master_ids.add(new_master_id)

                        # Add to newly created list (for final report)
                        newly_created.append({
                            'option_id': option_id,
                            'new_master_id': new_master_id,
                            'product_name': sku_record.get('Name_product_short_at_SKU_master', ''),
                            'cost': sku_record.get('Cost_product_at_SKU_master', 0),
                            'case_type': case_type,
                            'case_name': case_names.get(case_type, '알수없음'),
                            'base_master_id': base_master_id
                        })

                        # Update mapping for immediate use
                        self.sku_primary_map[option_id] = new_master_id

                        # Reload SKU list for next iteration
                        existing_skus = self.session.query(SKU_master).all()
                        existing_skus_list = [sku.to_dict() for sku in existing_skus]

                except Exception as e:
                    print(f"❌ GPT 처리 실패: {e}")
                    continue

            if newly_created:
                print(f"\n✨ GPT 자동 생성 완료: {len(newly_created)}건")
                for item in newly_created:
                    print(f"   옵션 {item['option_id']} → ID_master {item['new_master_id']} (케이스 {item['case_type']})")

                # Generate cost update report
                self._generate_cost_update_report(newly_created, filename)

        # Final matching statistics
        final_matched = df["ID_master"].notnull().sum()
        final_unmatched = df["ID_master"].isnull().sum()

        print(f"\n📊 최종 매칭 결과:")
        print(f"   성공: {final_matched}건")
        print(f"   실패: {final_unmatched}건")

        # Rename columns for matched data
        df_matched = df[df["ID_master"].notnull()].copy()
        df_matched.rename(columns=COLUMN_MAPPING_2P, inplace=True)

        # Normalize columns
        df_matched = normalize_numeric_columns(df_matched)
        df_matched = normalize_ratio_columns(df_matched)

        # Keep only valid columns
        valid_columns = ["ID_master"] + list(COLUMN_MAPPING_2P.values())
        df_matched = df_matched[[col for col in df_matched.columns if col in valid_columns]]

        # Normalize date
        df_matched = normalize_date_column(df_matched)

        # Save to database
        if not df_matched.empty:
            df_matched.to_sql(table_name, con=self.engine, if_exists='append', index=False)
            print(f"🛠 DB 저장 완료 ({len(df_matched)}건): {table_name}")
        else:
            print("ℹ️ 저장할 매칭된 데이터가 없습니다.")

        # Save unmatched file
        save_unmatched_file(df[df["ID_master"].isnull()], filepath)
