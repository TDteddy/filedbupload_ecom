"""
SKU Master generator for auto-created Coupang 2P products.
Generates new SKU_master records based on GPT analysis results.
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class SKUGenerator:
    """Generates new SKU_master records based on product analysis."""

    def __init__(self, session):
        """
        Initialize SKU generator.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

        # Initialize OpenAI client for SKU data generation
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        else:
            self.client = None
            print("⚠️ OpenAI API key not found. SKU generation will use template-based approach.")

    def generate_new_master_id(self, case_type, base_master_id, existing_master_ids):
        """
        Generate new ID_master based on case type.

        Args:
            case_type: int (1: quantity, 2: refund, 3: new)
            base_master_id: str or None (base product's ID_master)
            existing_master_ids: set of all existing ID_master values

        Returns:
            str: New ID_master
        """
        if case_type == 1:
            # Quantity variation: base_master_id + "-1", "-2", "-3"...
            return self._generate_suffix_id(base_master_id, existing_master_ids, numeric=True)

        elif case_type == 2:
            # Refund resale: base_master_id + "-A", "-B", "-C"...
            return self._generate_suffix_id(base_master_id, existing_master_ids, numeric=False)

        elif case_type == 3:
            # New product: Generate new numeric ID
            return self._generate_new_numeric_id(existing_master_ids)

        else:
            raise ValueError(f"Invalid case_type: {case_type}")

    def _generate_suffix_id(self, base_id, existing_ids, numeric=True):
        """
        Generate ID with suffix (numeric or alphabetic).

        Args:
            base_id: Base ID_master
            existing_ids: Set of existing IDs
            numeric: If True, use -1, -2, -3... else use -A, -B, -C...

        Returns:
            str: New ID with suffix
        """
        if not base_id:
            raise ValueError("base_id is required for suffix generation")

        if numeric:
            # Try -1, -2, -3...
            suffix = 1
            while True:
                new_id = f"{base_id}-{suffix}"
                if new_id not in existing_ids:
                    return new_id
                suffix += 1
        else:
            # Try -A, -B, -C...
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                new_id = f"{base_id}-{letter}"
                if new_id not in existing_ids:
                    return new_id

            # If all single letters are used, try AA, AB, AC...
            for first in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                for second in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                    new_id = f"{base_id}-{first}{second}"
                    if new_id not in existing_ids:
                        return new_id

        raise ValueError("Could not generate unique suffix ID")

    def _generate_new_numeric_id(self, existing_ids):
        """
        Generate new numeric ID_master.

        Args:
            existing_ids: Set of existing IDs

        Returns:
            str: New numeric ID
        """
        # Extract numeric IDs only (ignore IDs with suffixes like "42-1" or "42-A")
        numeric_ids = []
        for id_val in existing_ids:
            id_str = str(id_val)
            # Only consider pure numeric IDs
            if id_str.isdigit():
                numeric_ids.append(int(id_str))

        if numeric_ids:
            max_id = max(numeric_ids)
            new_id = max_id + 1
        else:
            new_id = 1

        return str(new_id)

    def generate_sku_record(self, case_type, new_master_id, unmatched_product, base_sku=None):
        """
        Generate complete SKU_master record.

        Args:
            case_type: int (1: quantity, 2: refund, 3: new)
            new_master_id: str (newly generated ID_master)
            unmatched_product: Dict with product info from Coupang 2P
            base_sku: Dict with base SKU_master data (None for case 3)

        Returns:
            Dict: Complete SKU_master record
        """
        if self.client and case_type in [1, 2] and base_sku:
            # Use GPT to generate modified SKU based on base product
            return self._generate_sku_with_gpt(case_type, new_master_id, unmatched_product, base_sku)
        else:
            # Use template-based approach
            return self._generate_sku_template(case_type, new_master_id, unmatched_product, base_sku)

    def _generate_sku_with_gpt(self, case_type, new_master_id, unmatched_product, base_sku):
        """Generate SKU record using GPT for intelligent field population."""
        case_description = {
            1: "수량변경 자동생성",
            2: "환불재판매"
        }

        prompt = f"""
## 작업: SKU_master 레코드 생성
케이스 타입: {case_type} ({case_description.get(case_type, '기타')})
새 ID_master: {new_master_id}

## 신규 상품 정보 (쿠팡 2P)
- 옵션 ID: {unmatched_product.get('option_id', 'N/A')}
- 옵션명: {unmatched_product.get('option_name', 'N/A')}
- 등록상품 ID: {unmatched_product.get('product_id', 'N/A')}
- 카테고리: {unmatched_product.get('category', 'N/A')}
- 판매방식: {unmatched_product.get('sales_type', 'N/A')}

## 기초 SKU 데이터 (참고용)
- ID_master: {base_sku.get('ID_master', 'N/A')}
- 제품명: {base_sku.get('Name_product_short_at_SKU_master', 'N/A')}
- 브랜드: {base_sku.get('Name_brand_at_SKU_master', 'N/A')}
- 원가: {base_sku.get('Cost_product_at_SKU_master', 'N/A')}
- 정가: {base_sku.get('Price_list_at_SKU_master', 'N/A')}
- 카테고리: {base_sku.get('Category_2p_1_coupang_at_SKU_master', 'N/A')}

## 요청사항
위 정보를 바탕으로 새로운 SKU_master 레코드를 생성하세요.

**케이스 1 (수량변경)**: 기초 데이터 대부분 복사, 원가/정가는 수량 비율에 맞게 조정
**케이스 2 (환불재판매)**: 기초 데이터 복사, 원가/정가는 할인 적용 (예: 70-80%)

다음 JSON 형식으로 응답하세요:
```json
{{
    "Name_product_short_at_SKU_master": "제품명 (옵션명 기반)",
    "Name_brand_at_SKU_master": "브랜드명",
    "Cost_product_at_SKU_master": 원가 (숫자),
    "Price_list_at_SKU_master": 정가 (숫자),
    "Category_2p_1_coupang_at_SKU_master": "카테고리",
    "Sales_type_coupang_at_SKU_master": "판매방식",
    "reasoning": "필드값 결정 근거"
}}
```
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 이커머스 상품 데이터 관리 전문가입니다. SKU 레코드를 생성할 때 논리적이고 일관성 있게 작성하세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1000
            )

            gpt_data = json.loads(response.choices[0].message.content)

            # Build complete SKU record
            sku_record = self._build_sku_record_from_gpt(
                new_master_id,
                unmatched_product,
                base_sku,
                gpt_data
            )

            print(f"✨ GPT 생성 근거: {gpt_data.get('reasoning', 'N/A')}")
            return sku_record

        except Exception as e:
            print(f"⚠️ GPT SKU 생성 실패, 템플릿 방식으로 전환: {e}")
            return self._generate_sku_template(case_type, new_master_id, unmatched_product, base_sku)

    def _build_sku_record_from_gpt(self, new_master_id, unmatched_product, base_sku, gpt_data):
        """Build SKU record combining GPT data and base SKU."""
        record = {
            'ID_master': new_master_id,

            # From GPT
            'Name_product_short_at_SKU_master': gpt_data.get('Name_product_short_at_SKU_master'),
            'Name_brand_at_SKU_master': gpt_data.get('Name_brand_at_SKU_master'),
            'Cost_product_at_SKU_master': gpt_data.get('Cost_product_at_SKU_master'),
            'Price_list_at_SKU_master': gpt_data.get('Price_list_at_SKU_master'),

            # From base SKU (copy over)
            'ID_erp_at_SKU_master': base_sku.get('ID_erp_at_SKU_master'),
            'ID_barcode_at_SKU_master': base_sku.get('ID_barcode_at_SKU_master'),
            'Product_line_at_SKU_master': base_sku.get('Product_line_at_SKU_master'),
            'Product_group_at_SKU_master': base_sku.get('Product_group_at_SKU_master'),
            'Product_type_at_SKU_master': base_sku.get('Product_type_at_SKU_master'),
            'Product_spec_at_SKU_master': base_sku.get('Product_spec_at_SKU_master'),

            # Coupang 2P specific (from unmatched product)
            'ID_option_vendor_coupang_at_SKU_master': unmatched_product.get('option_id'),
            'ID_product_sku_coupang_at_SKU_master': unmatched_product.get('product_id'),
            'Category_2p_1_coupang_at_SKU_master': gpt_data.get('Category_2p_1_coupang_at_SKU_master'),
            'Sales_type_coupang_at_SKU_master': gpt_data.get('Sales_type_coupang_at_SKU_master'),

            # Copy from base SKU
            'Category_2p_2_coupang_at_SKU_master': base_sku.get('Category_2p_2_coupang_at_SKU_master'),
            'Cost_fee_rate_2p_coupang_at_SKU_master': base_sku.get('Cost_fee_rate_2p_coupang_at_SKU_master'),
            'Cost_logistics_2p_coupang_at_SKU_master': base_sku.get('Cost_logistics_2p_coupang_at_SKU_master'),
            'Cost_delivery_2p_coupang_at_SKU_master': base_sku.get('Cost_delivery_2p_coupang_at_SKU_master'),
            'Cost_truck_coupang_at_SKU_master': base_sku.get('Cost_truck_coupang_at_SKU_master'),
            'URL_pc_coupang_at_SKU_master': base_sku.get('URL_pc_coupang_at_SKU_master'),
            'URL_m_coupang_at_SKU_master': base_sku.get('URL_m_coupang_at_SKU_master'),

            # Naver fields (copy from base)
            'Category_1_naver_at_SKU_master': base_sku.get('Category_1_naver_at_SKU_master'),
            'Category_2_naver_at_SKU_master': base_sku.get('Category_2_naver_at_SKU_master'),
            'Category_3_naver_at_SKU_master': base_sku.get('Category_3_naver_at_SKU_master'),
            'Category_4_naver_at_SKU_master': base_sku.get('Category_4_naver_at_SKU_master'),
            'ID_mall_product_naver_at_SKU_master': base_sku.get('ID_mall_product_naver_at_SKU_master'),
            'ID_product_naver_at_SKU_master': base_sku.get('ID_product_naver_at_SKU_master'),
            'URL_pc_naver_at_SKU_master': base_sku.get('URL_pc_naver_at_SKU_master'),
            'URL_m_naver_at_SKU_master': base_sku.get('URL_m_naver_at_SKU_master'),
            'Cost_fee_rate_naver_at_SKU_master': base_sku.get('Cost_fee_rate_naver_at_SKU_master'),
            'Cost_delivery_naver_at_SKU_master': base_sku.get('Cost_delivery_naver_at_SKU_master'),
            'Cost_truck_naver_at_SKU_master': base_sku.get('Cost_truck_naver_at_SKU_master'),

            # Cafe24 fields (copy from base)
            'ID_product_cafe24_at_SKU_master': base_sku.get('ID_product_cafe24_at_SKU_master'),
            'Cost_fee_rate_cafe24_at_SKU_master': base_sku.get('Cost_fee_rate_cafe24_at_SKU_master'),
            'Cost_delivery_cafe24_at_SKU_master': base_sku.get('Cost_delivery_cafe24_at_SKU_master'),
            'URL_pc_cafe24_at_SKU_master': base_sku.get('URL_pc_cafe24_at_SKU_master'),
            'URL_m_cafe24_at_SKU_master': base_sku.get('URL_m_cafe24_at_SKU_master'),
        }

        return record

    def _generate_sku_template(self, case_type, new_master_id, unmatched_product, base_sku):
        """Generate SKU record using template (fallback method)."""
        if case_type in [1, 2] and base_sku:
            # Copy from base and update Coupang IDs
            record = dict(base_sku)  # Copy all fields
            record['ID_master'] = new_master_id
            record['ID_option_vendor_coupang_at_SKU_master'] = unmatched_product.get('option_id')
            record['ID_product_sku_coupang_at_SKU_master'] = unmatched_product.get('product_id')
            record['Name_product_short_at_SKU_master'] = unmatched_product.get('option_name', base_sku.get('Name_product_short_at_SKU_master'))
            record['Category_2p_1_coupang_at_SKU_master'] = unmatched_product.get('category', base_sku.get('Category_2p_1_coupang_at_SKU_master'))
            record['Sales_type_coupang_at_SKU_master'] = unmatched_product.get('sales_type', base_sku.get('Sales_type_coupang_at_SKU_master'))

            # Adjust price for case 1 (quantity) or case 2 (refund)
            if case_type == 1:
                # Keep original price (template doesn't know quantity ratio)
                pass
            elif case_type == 2:
                # Apply 20% discount for refund items
                if record.get('Cost_product_at_SKU_master'):
                    record['Cost_product_at_SKU_master'] = record['Cost_product_at_SKU_master'] * 0.8
                if record.get('Price_list_at_SKU_master'):
                    record['Price_list_at_SKU_master'] = record['Price_list_at_SKU_master'] * 0.8

        else:
            # New product - create minimal record
            record = {
                'ID_master': new_master_id,
                'Name_product_short_at_SKU_master': unmatched_product.get('option_name'),
                'ID_option_vendor_coupang_at_SKU_master': unmatched_product.get('option_id'),
                'ID_product_sku_coupang_at_SKU_master': unmatched_product.get('product_id'),
                'Category_2p_1_coupang_at_SKU_master': unmatched_product.get('category'),
                'Sales_type_coupang_at_SKU_master': unmatched_product.get('sales_type'),
            }

        return record
