#!/usr/bin/env python
"""
Main execution script for e-commerce data upload system.
Processes Excel and CSV files from various platforms and uploads to MySQL database.
"""

import glob
import sys
import argparse
from src.database import DatabaseManager
from src.utils import load_sku_mappings
from src.processors import FileProcessor
from src.sku_daily_updater import SKUDailyUpdater


def main():
    """Main execution function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='E-commerce Data Upload System')
    parser.add_argument('--all-only', action='store_true',
                        help='쿠팡 2P 파일을 ALL 테이블에만 업로드 (매칭 스킵)')
    parser.add_argument('--sku-daily-update', action='store_true',
                        help='SKU Daily Update 실행 (날짜별 가격 업데이트)')
    args = parser.parse_args()

    print("=" * 60)
    print("E-commerce Data Upload System")
    if args.all_only:
        print("모드: 쿠팡 2P ALL 전용 (매칭 없음)")
    if args.sku_daily_update:
        print("모드: SKU Daily Update")
    print("=" * 60)

    # Initialize database connection
    try:
        print("\n🔌 데이터베이스 연결 중...")
        db_manager = DatabaseManager()
        session = db_manager.get_session()
        engine = db_manager.get_engine()
        print("✅ 데이터베이스 연결 성공")
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        print("\n💡 .env 파일 설정을 확인하세요:")
        print("   - DB_HOST")
        print("   - DB_USER")
        print("   - DB_PASSWORD")
        print("   - DB_NAME")
        sys.exit(1)

    # SKU Daily Update mode
    if args.sku_daily_update:
        print("\n" + "=" * 60)
        print("SKU Daily Update 모드")
        print("=" * 60)

        # Get date input from user
        print("\n📅 날짜 입력 (형식: YYYY-MM-DD 또는 YYYY-MM-DD~YYYY-MM-DD)")
        print("예시: 2024-01-15 (단일 날짜) 또는 2024-01-01~2024-01-31 (기간)")
        date_input = input("날짜 입력: ").strip()

        try:
            updater = SKUDailyUpdater(db_manager, session)
            start_date, end_date = updater.parse_date_input(date_input)
            updater.update_sku_daily(start_date, end_date)
        except Exception as e:
            print(f"❌ SKU Daily Update 실패: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db_manager.close()
            print("\n🔌 데이터베이스 연결 종료")

        sys.exit(0)

    # Load SKU mappings
    try:
        sku_mappings = load_sku_mappings(session)
    except Exception as e:
        print(f"❌ SKU 매핑 테이블 로딩 실패: {e}")
        print("\n💡 models.py 파일과 데이터베이스 테이블을 확인하세요:")
        print("   - SKU_master 테이블")
        print("   - coupang_1p_auto_created_vender_ID 테이블")
        db_manager.close()
        sys.exit(1)

    # Initialize file processor with GPT support
    processor = FileProcessor(engine, sku_mappings, db_manager=db_manager, session=session, all_only_mode=args.all_only)

    # Find files to process
    excel_files = glob.glob("*.xlsx")
    csv_files = glob.glob("*.csv")
    all_files = excel_files + csv_files

    if not all_files:
        print("\n📂 처리할 파일이 없습니다.")
        print("   현재 디렉토리에 .xlsx 또는 .csv 파일을 배치하세요.")
        db_manager.close()
        sys.exit(0)

    print(f"\n📊 발견된 파일: {len(all_files)}개")
    for f in all_files:
        print(f"   - {f}")

    # Process each file
    success_count = 0
    error_count = 0

    for file in all_files:
        try:
            processor.process_file(file)
            success_count += 1
        except Exception as e:
            print(f"❌ 파일 처리 실패 ({file}): {e}")
            error_count += 1

    # Print summary
    print("\n" + "=" * 60)
    print("처리 완료")
    print("=" * 60)
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {error_count}개")
    print("=" * 60)

    # Close database connection
    db_manager.close()
    print("\n🔌 데이터베이스 연결 종료")


if __name__ == "__main__":
    main()
