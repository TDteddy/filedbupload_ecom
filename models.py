"""
SQLAlchemy models for database tables.
Complete SKU_master model with all fields.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Boolean, DECIMAL
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SKU_master(Base):
    """
    SKU Master table - central product mapping across all platforms.
    Links products from Coupang, Naver, Cafe24 with a unified master ID.
    """
    __tablename__ = 'SKU_master'

    # Primary key
    ID_master = Column(String(50), primary_key=True)

    # Basic product information
    ID_erp_at_SKU_master = Column(String(100))
    ID_barcode_at_SKU_master = Column(String(100))
    Name_brand_at_SKU_master = Column(String(200))
    Product_line_at_SKU_master = Column(String(200))
    Product_group_at_SKU_master = Column(String(200))
    Name_product_short_at_SKU_master = Column(String(500))
    Product_type_at_SKU_master = Column(String(200))
    Product_spec_at_SKU_master = Column(String(500))

    # Pricing
    Price_list_at_SKU_master = Column(DECIMAL(15, 2))
    Cost_product_at_SKU_master = Column(DECIMAL(15, 2))

    # Naver platform fields
    Category_1_naver_at_SKU_master = Column(String(200))
    Category_2_naver_at_SKU_master = Column(String(200))
    Category_3_naver_at_SKU_master = Column(String(200))
    Category_4_naver_at_SKU_master = Column(String(200))
    ID_mall_product_naver_at_SKU_master = Column(String(100))
    ID_product_naver_at_SKU_master = Column(String(100), index=True)
    URL_pc_naver_at_SKU_master = Column(Text)
    URL_m_naver_at_SKU_master = Column(Text)
    Cost_fee_rate_naver_at_SKU_master = Column(DECIMAL(5, 4))
    Cost_delivery_naver_at_SKU_master = Column(DECIMAL(15, 2))
    Cost_truck_naver_at_SKU_master = Column(DECIMAL(15, 2))

    # Coupang platform fields
    Sales_type_coupang_at_SKU_master = Column(String(50))  # 1P or 2P
    ID_option_vendor_coupang_at_SKU_master = Column(String(100), index=True)
    ID_product_sku_coupang_at_SKU_master = Column(String(100), index=True)
    URL_pc_coupang_at_SKU_master = Column(Text)
    URL_m_coupang_at_SKU_master = Column(Text)

    # Coupang 1P categories
    Category_1p_1_coupang_at_SKU_master = Column(String(200))
    Category_1p_2_coupang_at_SKU_master = Column(String(200))
    Category_1p_3_coupang_at_SKU_master = Column(String(200))

    # Coupang 2P categories and costs
    Category_2p_1_coupang_at_SKU_master = Column(String(200))
    Category_2p_2_coupang_at_SKU_master = Column(String(200))
    Cost_fee_rate_2p_coupang_at_SKU_master = Column(DECIMAL(5, 4))
    Cost_logistics_2p_coupang_at_SKU_master = Column(DECIMAL(15, 2))
    Cost_delivery_2p_coupang_at_SKU_master = Column(DECIMAL(15, 2))
    Cost_truck_coupang_at_SKU_master = Column(DECIMAL(15, 2))

    # Cafe24 platform fields
    ID_product_cafe24_at_SKU_master = Column(String(100), index=True)
    Cost_fee_rate_cafe24_at_SKU_master = Column(DECIMAL(5, 4))
    Cost_delivery_cafe24_at_SKU_master = Column(DECIMAL(15, 2))
    URL_pc_cafe24_at_SKU_master = Column(Text)
    URL_m_cafe24_at_SKU_master = Column(Text)

    def __repr__(self):
        return f"<SKU_master(ID={self.ID_master}, Name={self.Name_product_short_at_SKU_master})>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'ID_master': self.ID_master,
            'ID_erp_at_SKU_master': self.ID_erp_at_SKU_master,
            'ID_barcode_at_SKU_master': self.ID_barcode_at_SKU_master,
            'Name_brand_at_SKU_master': self.Name_brand_at_SKU_master,
            'Product_line_at_SKU_master': self.Product_line_at_SKU_master,
            'Product_group_at_SKU_master': self.Product_group_at_SKU_master,
            'Name_product_short_at_SKU_master': self.Name_product_short_at_SKU_master,
            'Product_type_at_SKU_master': self.Product_type_at_SKU_master,
            'Product_spec_at_SKU_master': self.Product_spec_at_SKU_master,
            'Price_list_at_SKU_master': float(self.Price_list_at_SKU_master) if self.Price_list_at_SKU_master else None,
            'Cost_product_at_SKU_master': float(self.Cost_product_at_SKU_master) if self.Cost_product_at_SKU_master else None,
            'Category_1_naver_at_SKU_master': self.Category_1_naver_at_SKU_master,
            'Category_2_naver_at_SKU_master': self.Category_2_naver_at_SKU_master,
            'Category_3_naver_at_SKU_master': self.Category_3_naver_at_SKU_master,
            'Category_4_naver_at_SKU_master': self.Category_4_naver_at_SKU_master,
            'ID_mall_product_naver_at_SKU_master': self.ID_mall_product_naver_at_SKU_master,
            'ID_product_naver_at_SKU_master': self.ID_product_naver_at_SKU_master,
            'URL_pc_naver_at_SKU_master': self.URL_pc_naver_at_SKU_master,
            'URL_m_naver_at_SKU_master': self.URL_m_naver_at_SKU_master,
            'Cost_fee_rate_naver_at_SKU_master': float(self.Cost_fee_rate_naver_at_SKU_master) if self.Cost_fee_rate_naver_at_SKU_master else None,
            'Cost_delivery_naver_at_SKU_master': float(self.Cost_delivery_naver_at_SKU_master) if self.Cost_delivery_naver_at_SKU_master else None,
            'Cost_truck_naver_at_SKU_master': float(self.Cost_truck_naver_at_SKU_master) if self.Cost_truck_naver_at_SKU_master else None,
            'Sales_type_coupang_at_SKU_master': self.Sales_type_coupang_at_SKU_master,
            'ID_option_vendor_coupang_at_SKU_master': self.ID_option_vendor_coupang_at_SKU_master,
            'ID_product_sku_coupang_at_SKU_master': self.ID_product_sku_coupang_at_SKU_master,
            'URL_pc_coupang_at_SKU_master': self.URL_pc_coupang_at_SKU_master,
            'URL_m_coupang_at_SKU_master': self.URL_m_coupang_at_SKU_master,
            'Category_1p_1_coupang_at_SKU_master': self.Category_1p_1_coupang_at_SKU_master,
            'Category_1p_2_coupang_at_SKU_master': self.Category_1p_2_coupang_at_SKU_master,
            'Category_1p_3_coupang_at_SKU_master': self.Category_1p_3_coupang_at_SKU_master,
            'Category_2p_1_coupang_at_SKU_master': self.Category_2p_1_coupang_at_SKU_master,
            'Category_2p_2_coupang_at_SKU_master': self.Category_2p_2_coupang_at_SKU_master,
            'Cost_fee_rate_2p_coupang_at_SKU_master': float(self.Cost_fee_rate_2p_coupang_at_SKU_master) if self.Cost_fee_rate_2p_coupang_at_SKU_master else None,
            'Cost_logistics_2p_coupang_at_SKU_master': float(self.Cost_logistics_2p_coupang_at_SKU_master) if self.Cost_logistics_2p_coupang_at_SKU_master else None,
            'Cost_delivery_2p_coupang_at_SKU_master': float(self.Cost_delivery_2p_coupang_at_SKU_master) if self.Cost_delivery_2p_coupang_at_SKU_master else None,
            'Cost_truck_coupang_at_SKU_master': float(self.Cost_truck_coupang_at_SKU_master) if self.Cost_truck_coupang_at_SKU_master else None,
            'ID_product_cafe24_at_SKU_master': self.ID_product_cafe24_at_SKU_master,
            'Cost_fee_rate_cafe24_at_SKU_master': float(self.Cost_fee_rate_cafe24_at_SKU_master) if self.Cost_fee_rate_cafe24_at_SKU_master else None,
            'Cost_delivery_cafe24_at_SKU_master': float(self.Cost_delivery_cafe24_at_SKU_master) if self.Cost_delivery_cafe24_at_SKU_master else None,
            'URL_pc_cafe24_at_SKU_master': self.URL_pc_cafe24_at_SKU_master,
            'URL_m_cafe24_at_SKU_master': self.URL_m_cafe24_at_SKU_master,
        }


class coupang_1p_auto_created_vender_ID(Base):
    """
    Coupang 1P auto-created vendor ID mapping table.
    Maps auto-created vendor option IDs to SKU IDs for legacy data.

    Note: This table is used for backward compatibility with existing data.
    New SKU creation is handled by GPT analysis.
    """
    __tablename__ = 'coupang_1p_auto_created_vender_ID'

    Index = Column(Integer, primary_key=True, autoincrement=True)
    ID_option_vendor_coupang_at_coupang_1p_auto_created_vender_ID = Column(String(255), index=True)
    ID_product_sku_coupang_at_coupang_1p_auto_created_vender_ID = Column(String(255), index=True)

    def __repr__(self):
        return f"<coupang_1p_auto_created_vender_ID(Index={self.Index})>"


class SKU_daily_update(Base):
    """
    SKU Daily Update table - daily price tracking across platforms.
    Stores final prices calculated from sales data for each SKU per day.
    """
    __tablename__ = 'SKU_daily_update'

    # Composite primary key
    Index = Column(Integer, primary_key=True, autoincrement=True)
    ID_master = Column(String(255), nullable=False, index=True)
    Date = Column(Date, nullable=False, index=True)

    # Naver prices
    Price_display_naver_at_SKU_daily_update = Column(Integer)
    Price_final_naver_at_SKU_daily_update = Column(Integer)
    Price_discount_naver_at_SKU_daily_update = Column(Integer)
    Name_product_display_naver_at_SKU_daily_update = Column(String(255))
    Cost_discount_coupon_naver_at_SKU_daily_update = Column(Integer)

    # Coupang prices
    Price_display_coupang_at_SKU_daily_update = Column(Integer)
    Price_final_coupang_at_SKU_daily_update = Column(Integer)
    Price_supply_1p_coupang_at_SKU_daily_update = Column(Integer)
    Price_discount_coupang_at_SKU_daily_update = Column(Integer)
    Name_product_display_coupang_at_SKU_daily_update = Column(String(255))
    Cost_incentive_1p_coupang_at_SKU_daily_update = Column(Integer)
    Cost_DA_1P_at_SKU_daily_update = Column(Integer)

    def __repr__(self):
        return f"<SKU_daily_update(ID={self.ID_master}, Date={self.Date})>"


class sales_report_naver_etc(Base):
    """
    Naver sales report table - ETC channel sales data.
    Contains 14-day sales and order count data for Naver products.
    """
    __tablename__ = 'sales_report_naver_etc'

    Index = Column(Integer, primary_key=True, autoincrement=True)
    ID_master = Column(String(255))
    Date = Column(Date)
    Category_1_naver_at_sales_report_naver_etc = Column(String(255))
    Category_2_naver_at_sales_report_naver_etc = Column(String(255))
    Category_3_naver_at_sales_report_naver_etc = Column(String(255))
    Category_4_naver_at_sales_report_naver_etc = Column(String(255))
    Name_product_at_sales_report_naver_etc = Column(String(255))
    ID_product_at_sales_report_naver_etc = Column(String(255))
    Channel_group_at_sales_report_naver_etc = Column(String(255))
    Channel_name_at_sales_report_naver_etc = Column(String(255))
    Channel_detail_at_sales_report_naver_etc = Column(String(255))
    Count_order_14d_at_sales_report_naver_etc = Column(Integer)
    Sales_order_14d_at_sales_report_naver_etc = Column(Integer)

    def __repr__(self):
        return f"<sales_report_naver_etc(ID={self.ID_master}, Date={self.Date})>"
