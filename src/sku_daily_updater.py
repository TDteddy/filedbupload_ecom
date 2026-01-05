"""
SKU Daily Update module.
Updates daily price information for all SKUs based on sales reports.
"""

from datetime import datetime, timedelta
from sqlalchemy import and_, func
from models import SKU_master, SKU_daily_update


class SKUDailyUpdater:
    """Handles daily SKU price updates from sales data."""

    def __init__(self, db_manager, session):
        """
        Initialize SKU Daily Updater.

        Args:
            db_manager: DatabaseManager instance
            session: SQLAlchemy session
        """
        self.db_manager = db_manager
        self.session = session
        self.engine = db_manager.get_engine()

    def update_sku_daily(self, start_date, end_date=None):
        """
        Update SKU daily records for given date range.

        Args:
            start_date: datetime.date - Start date
            end_date: datetime.date or None - End date (None for single date)
        """
        # If end_date is not provided, use start_date (single day)
        if end_date is None:
            end_date = start_date

        print(f"\n📅 SKU Daily Update: {start_date} ~ {end_date}")

        # Get all master IDs
        all_master_ids = self.session.query(SKU_master.ID_master).all()
        all_master_ids = [row[0] for row in all_master_ids]

        print(f"📊 전체 SKU 개수: {len(all_master_ids)}개")

        # Process each date
        current_date = start_date
        while current_date <= end_date:
            print(f"\n🔄 처리 중: {current_date}")
            self._process_single_date(current_date, all_master_ids)
            current_date += timedelta(days=1)

        print(f"\n✅ SKU Daily Update 완료!")

    def _process_single_date(self, target_date, all_master_ids):
        """
        Process SKU daily update for a single date.

        Args:
            target_date: datetime.date - Target date to process
            all_master_ids: list - List of all ID_master values
        """
        # Calculate final prices from sales reports
        coupang_final_prices = self._calculate_coupang_final_prices(target_date)
        naver_final_prices = self._calculate_naver_final_prices(target_date)

        # Get previous day's data for fallback
        previous_date = target_date - timedelta(days=1)
        previous_day_data = self._get_previous_day_data(previous_date)

        # Process each master ID
        created_count = 0
        updated_count = 0

        for master_id in all_master_ids:
            # Check if record already exists
            existing_record = self.session.query(SKU_daily_update).filter(
                and_(
                    SKU_daily_update.ID_master == master_id,
                    SKU_daily_update.Date == target_date
                )
            ).first()

            # Determine final prices
            coupang_price = coupang_final_prices.get(master_id)
            naver_price = naver_final_prices.get(master_id)

            # Fallback to previous day if no sales data
            if coupang_price is None and master_id in previous_day_data:
                coupang_price = previous_day_data[master_id].get('Price_final_coupang_at_SKU_daily_update')

            if naver_price is None and master_id in previous_day_data:
                naver_price = previous_day_data[master_id].get('Price_final_naver_at_SKU_daily_update')

            if existing_record:
                # Update existing record
                existing_record.Price_final_coupang_at_SKU_daily_update = coupang_price
                existing_record.Price_final_naver_at_SKU_daily_update = naver_price
                updated_count += 1
            else:
                # Create new record
                new_record = SKU_daily_update(
                    ID_master=master_id,
                    Date=target_date,
                    Price_final_coupang_at_SKU_daily_update=coupang_price,
                    Price_final_naver_at_SKU_daily_update=naver_price
                )
                self.session.add(new_record)
                created_count += 1

        # Commit changes
        self.session.commit()
        print(f"   ✅ 생성: {created_count}건, 업데이트: {updated_count}건")

    def _calculate_coupang_final_prices(self, target_date):
        """
        Calculate final prices from Coupang sales reports.
        Final price = Sales amount / Quantity sold

        Args:
            target_date: datetime.date

        Returns:
            dict: {ID_master: final_price}
        """
        final_prices = {}

        # Query Coupang 1P sales report
        query_1p = f"""
        SELECT
            sm.ID_master,
            SUM(sr.Sales_GMV_at_sales_report_coupang_1p) as total_sales,
            SUM(sr.Qty_sales_at_sales_report_coupang_1p) as total_qty
        FROM sales_report_coupang_1p sr
        INNER JOIN SKU_master sm
            ON sr.ID_option_coupang_1p_at_sales_report_coupang_1p = sm.ID_option_vendor_coupang_at_SKU_master
        WHERE sr.Date = '{target_date}'
        GROUP BY sm.ID_master
        HAVING total_qty > 0
        """

        try:
            result_1p = self.engine.execute(query_1p)
            for row in result_1p:
                master_id, total_sales, total_qty = row
                if total_qty > 0 and total_sales is not None:
                    final_prices[master_id] = float(total_sales) / float(total_qty)
        except Exception as e:
            print(f"   ⚠️ 쿠팡 1P 데이터 조회 실패: {e}")

        # Query Coupang 2P sales report
        query_2p = f"""
        SELECT
            sm.ID_master,
            SUM(sr.Sales_total_amount_at_sales_report_coupang_2p) as total_sales,
            SUM(sr.Qty_sales_total_at_sales_report_coupang_2p) as total_qty
        FROM sales_report_coupang_2p sr
        INNER JOIN SKU_master sm
            ON sr.ID_option_coupang_2p_at_sales_report_coupang_2p = sm.ID_option_vendor_coupang_at_SKU_master
        WHERE sr.Date = '{target_date}'
        GROUP BY sm.ID_master
        HAVING total_qty > 0
        """

        try:
            result_2p = self.engine.execute(query_2p)
            for row in result_2p:
                master_id, total_sales, total_qty = row
                if total_qty > 0 and total_sales is not None:
                    final_prices[master_id] = float(total_sales) / float(total_qty)
        except Exception as e:
            print(f"   ⚠️ 쿠팡 2P 데이터 조회 실패: {e}")

        return final_prices

    def _calculate_naver_final_prices(self, target_date):
        """
        Calculate final prices from Naver sales reports.
        Final price = Payment amount / Payment count

        Args:
            target_date: datetime.date

        Returns:
            dict: {ID_master: final_price}
        """
        final_prices = {}

        # Query Naver sales report
        query_naver = f"""
        SELECT
            sm.ID_master,
            SUM(sr.Sales_order_14d_at_sales_report_naver_etc) as total_sales,
            SUM(sr.Count_order_14d_at_sales_report_naver_etc) as total_count
        FROM sales_report_naver_etc sr
        INNER JOIN SKU_master sm
            ON sr.ID_product_at_sales_report_naver_etc = sm.ID_product_naver_at_SKU_master
        WHERE sr.Date = '{target_date}'
        GROUP BY sm.ID_master
        HAVING total_count > 0
        """

        try:
            result_naver = self.engine.execute(query_naver)
            for row in result_naver:
                master_id, total_sales, total_count = row
                if total_count > 0 and total_sales is not None:
                    final_prices[master_id] = float(total_sales) / float(total_count)
        except Exception as e:
            print(f"   ⚠️ 네이버 데이터 조회 실패: {e}")

        return final_prices

    def _get_previous_day_data(self, previous_date):
        """
        Get previous day's SKU daily data for fallback.

        Args:
            previous_date: datetime.date

        Returns:
            dict: {ID_master: {field: value}}
        """
        previous_data = {}

        records = self.session.query(SKU_daily_update).filter(
            SKU_daily_update.Date == previous_date
        ).all()

        for record in records:
            previous_data[record.ID_master] = {
                'Price_final_coupang_at_SKU_daily_update': record.Price_final_coupang_at_SKU_daily_update,
                'Price_final_naver_at_SKU_daily_update': record.Price_final_naver_at_SKU_daily_update,
            }

        return previous_data

    def parse_date_input(self, date_str):
        """
        Parse date input string.
        Supports single date or date range.

        Args:
            date_str: str - Date string (YYYY-MM-DD or YYYY-MM-DD~YYYY-MM-DD)

        Returns:
            tuple: (start_date, end_date)
        """
        date_str = date_str.strip()

        # Check if it's a date range
        if '~' in date_str or '-' in date_str.split('-', 3)[-1]:
            # Try splitting by ~
            parts = date_str.split('~')
            if len(parts) == 2:
                start_date = datetime.strptime(parts[0].strip(), '%Y-%m-%d').date()
                end_date = datetime.strptime(parts[1].strip(), '%Y-%m-%d').date()
                return start_date, end_date

        # Single date
        single_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        return single_date, single_date
