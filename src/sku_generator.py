"""
SKU Master generator for auto-created Coupang 2P products.
Generates new SKU_master records based on GPT analysis results.
"""

import os
import json
import re
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

        # Brand to prefix mapping
        self.brand_prefix_map = {
            '닥터시드': 'D',
            '딸로': 'T',
            '테르스': 'S',
            '에이더': None,  # Random 3-letter prefix for 에이더
        }

    def _get_brand_prefix(self, brand_name):
        """
        Get prefix for a brand name.

        Args:
            brand_name: Brand name string

        Returns:
            str or None: Prefix (e.g., 'D', 'T', 'S') or None for random prefix
        """
        if not brand_name:
            return None

        # Exact match
        if brand_name in self.brand_prefix_map:
            return self.brand_prefix_map[brand_name]

        # Fuzzy match (contains)
        for brand_key, prefix in self.brand_prefix_map.items():
            if brand_key in brand_name or brand_name in brand_key:
                return prefix

        return None

    def _extract_quantity_from_name(self, product_name):
        """
        Extract quantity from product name.

        Args:
            product_name: Product name string

        Returns:
            int or None: Extracted quantity (e.g., "2병" → 2, "3개입" → 3)
        """
        if not product_name:
            return None

        # Patterns to match: "2병", "3개", "5개입", "10팩" etc.
        patterns = [
            r'(\d+)\s*병',
            r'(\d+)\s*개입',
            r'(\d+)\s*개',
            r'(\d+)\s*팩',
            r'(\d+)\s*입',
            r'(\d+)\s*구',
        ]

        for pattern in patterns:
            match = re.search(pattern, product_name)
            if match:
                return int(match.group(1))

        return None

    def validate_and_correct_base_sku(self, selected_base_id, all_skus):
        """
        Validate if the selected base SKU has the smallest quantity.
        If not, find and return the SKU with the smallest quantity.

        Args:
            selected_base_id: str - ID_master of the base SKU selected by GPT
            all_skus: list - List of all existing SKU_master records

        Returns:
            tuple: (corrected_base_sku_dict, was_corrected: bool)
        """
        from models import SKU_master

        # Find the selected base SKU
        selected_base = None
        for sku in all_skus:
            if isinstance(sku, dict):
                if sku.get('ID_master') == selected_base_id:
                    selected_base = sku
                    break
            elif hasattr(sku, 'ID_master'):
                if sku.ID_master == selected_base_id:
                    # Convert SQLAlchemy object to dict
                    selected_base = {col.name: getattr(sku, col.name) for col in sku.__table__.columns}
                    break

        if not selected_base:
            print(f"⚠️ 선택된 base_master_id '{selected_base_id}'를 찾을 수 없습니다.")
            return None, False

        # Extract base product info for similarity comparison
        base_brand = selected_base.get('Name_brand_at_SKU_master', '')
        base_category = selected_base.get('Category_2p_1_coupang_at_SKU_master', '')
        base_product_line = selected_base.get('Product_line_at_SKU_master', '')

        # Find all similar SKUs (same brand, category, or product line)
        similar_skus = []
        for sku in all_skus:
            if isinstance(sku, dict):
                sku_dict = sku
            elif hasattr(sku, 'ID_master'):
                sku_dict = {col.name: getattr(sku, col.name) for col in sku.__table__.columns}
            else:
                continue

            # Skip if ID has suffix (e.g., "42-1", "42-A") - these are variations
            sku_id = str(sku_dict.get('ID_master', ''))
            if '-' in sku_id:
                continue

            # Check similarity
            sku_brand = sku_dict.get('Name_brand_at_SKU_master', '')
            sku_category = sku_dict.get('Category_2p_1_coupang_at_SKU_master', '')
            sku_product_line = sku_dict.get('Product_line_at_SKU_master', '')

            is_similar = False
            if base_brand and sku_brand and base_brand == sku_brand:
                is_similar = True
            if base_category and sku_category and base_category == sku_category:
                is_similar = True
            if base_product_line and sku_product_line and base_product_line == sku_product_line:
                is_similar = True

            if is_similar:
                similar_skus.append(sku_dict)

        if not similar_skus:
            # No similar SKUs found, use the selected one
            return selected_base, False

        # Extract quantities from all similar SKUs
        sku_quantities = []
        for sku in similar_skus:
            product_name = sku.get('Name_product_short_at_SKU_master', '')
            qty = self._extract_quantity_from_name(product_name)
            if qty is not None:
                sku_quantities.append((sku, qty))

        if not sku_quantities:
            # No quantities extracted, use the selected one
            return selected_base, False

        # Find the SKU with the smallest quantity
        sku_quantities.sort(key=lambda x: x[1])  # Sort by quantity
        smallest_sku, smallest_qty = sku_quantities[0]

        # Check if the selected base is already the smallest
        selected_base_name = selected_base.get('Name_product_short_at_SKU_master', '')
        selected_base_qty = self._extract_quantity_from_name(selected_base_name)

        if selected_base.get('ID_master') == smallest_sku.get('ID_master'):
            # Already optimal
            print(f"✅ Base SKU 검증: '{selected_base_name}' ({selected_base_qty}개) - 이미 최소 개수 단위")
            return selected_base, False
        else:
            # Need correction
            smallest_name = smallest_sku.get('Name_product_short_at_SKU_master', '')
            print(f"🔄 Base SKU 자동 보정:")
            print(f"   GPT 선택: '{selected_base_name}' ({selected_base_qty}개) → ID: {selected_base.get('ID_master')}")
            print(f"   자동 보정: '{smallest_name}' ({smallest_qty}개) → ID: {smallest_sku.get('ID_master')}")
            return smallest_sku, True

    def generate_new_master_id(self, case_type, base_master_id, existing_master_ids, brand_name=None):
        """
        Generate new ID_master based on case type.

        Args:
            case_type: int (1: count(same package), 2: refund, 3: new(incl. package change))
            base_master_id: str or None (base product's ID_master)
            existing_master_ids: set of all existing ID_master values
            brand_name: str or None (brand name for case 3 to determine prefix)

        Returns:
            str: New ID_master
        """
        if case_type == 1:
            # Count variation (same package): base_master_id + "-1", "-2", "-3"...
            return self._generate_suffix_id(base_master_id, existing_master_ids, numeric=True)

        elif case_type == 2:
            # Refund resale: base_master_id + "-A", "-B", "-C"...
            return self._generate_suffix_id(base_master_id, existing_master_ids, numeric=False)

        elif case_type == 3:
            # New product: Generate new numeric ID with brand-specific prefix
            return self._generate_new_numeric_id(existing_master_ids, brand_name)

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

    def _generate_new_numeric_id(self, existing_ids, brand_name=None):
        """
        Generate new ID_master based on brand.

        Format: prefix + 6-digit number + A
        - 닥터시드: D000001A, D000002A, ...
        - 딸로: T000001A, T000002A, ...
        - 테르스: S000001A, S000002A, ...
        - 에이더: ABC000001A (random 3-letter prefix)
        - Unknown: S000001A (default to 'S')

        Args:
            existing_ids: Set of existing IDs
            brand_name: Brand name to determine prefix

        Returns:
            str: New ID (e.g., "D000001A")
        """
        import re
        import random
        import string

        # Determine prefix based on brand
        target_prefix = self._get_brand_prefix(brand_name) if brand_name else None

        # For 에이더, generate random 3-letter prefix
        if brand_name and '에이더' in brand_name:
            # Generate random 3-letter prefix
            while True:
                target_prefix = ''.join(random.choices(string.ascii_uppercase, k=3))
                # Check if this prefix already exists
                prefix_exists = any(
                    str(id_val).startswith(target_prefix)
                    for id_val in existing_ids
                    if not '-' in str(id_val)
                )
                if not prefix_exists:
                    break
            prefix_length = 3
        elif target_prefix:
            prefix_length = 1
        else:
            # Default: use 'S' if no brand match
            target_prefix = 'S'
            prefix_length = 1
            print(f"⚠️ 브랜드 '{brand_name}' 매칭 실패, 기본 prefix 'S' 사용")

        # Extract numeric parts from existing IDs with same prefix
        numeric_parts = []

        # New format: prefix(1 or 3 chars) + 6 digits + A
        pattern_new_1 = re.compile(r'^([A-Z])(\d{6})A$')
        pattern_new_3 = re.compile(r'^([A-Z]{3})(\d{6})A$')
        # Old format: prefix(1 char) + variable digits (backward compatibility)
        pattern_old = re.compile(r'^([A-Z])(\d+)$')

        for id_val in existing_ids:
            id_str = str(id_val)

            # Skip IDs with suffixes (contains '-')
            if '-' in id_str:
                continue

            # Try new format patterns
            if prefix_length == 1:
                match = pattern_new_1.match(id_str)
                if match and match.group(1) == target_prefix:
                    numeric_parts.append(int(match.group(2)))
                    continue
                # Backward compatibility: old format
                match = pattern_old.match(id_str)
                if match and match.group(1) == target_prefix:
                    numeric_parts.append(int(match.group(2)))
            elif prefix_length == 3:
                match = pattern_new_3.match(id_str)
                if match and match.group(1) == target_prefix:
                    numeric_parts.append(int(match.group(2)))

        # Generate new number
        if numeric_parts:
            new_number = max(numeric_parts) + 1
        else:
            new_number = 1

        # Format: 6 digits with leading zeros
        new_number_str = str(new_number).zfill(6)
        new_id = f"{target_prefix}{new_number_str}A"

        print(f"🏷️ 브랜드 '{brand_name}' → Prefix '{target_prefix}' → ID: {new_id}")
        return new_id

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
            1: "개수변경 자동생성 (같은 패키지)",
            2: "환불재판매"
        }

        # For case 1, calculate cost based on quantity ratio
        calculated_cost = None
        calculated_price = None
        quantity_ratio_info = ""

        if case_type == 1:
            base_name = base_sku.get('Name_product_short_at_SKU_master', '')
            new_name = unmatched_product.get('option_name', '')

            base_qty = self._extract_quantity_from_name(base_name)
            new_qty = self._extract_quantity_from_name(new_name)

            if base_qty and new_qty and base_qty > 0:
                ratio = new_qty / base_qty
                base_cost = base_sku.get('Cost_product_at_SKU_master') or 0
                base_price = base_sku.get('Price_list_at_SKU_master') or 0

                if base_cost > 0:
                    calculated_cost = base_cost * ratio
                    calculated_price = base_price * ratio
                    quantity_ratio_info = f"\n**개수 비율 계산됨**: {base_qty}개 → {new_qty}개 (비율: {ratio:.2f}배)\n- 계산된 원가: {calculated_cost:.0f}원\n- 계산된 정가: {calculated_price:.0f}원"

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
{quantity_ratio_info}

## 요청사항
위 정보를 바탕으로 새로운 SKU_master 레코드를 생성하세요.

**케이스 1 (개수변경)**: {'원가/정가는 위 계산값 사용' if calculated_cost else '기초 데이터 대부분 복사, 원가/정가는 개수 비율에 맞게 조정'}
**케이스 2 (환불재판매)**: 기초 데이터 복사, 원가/정가는 기초 데이터 그대로 사용 (할인 없음)

다음 JSON 형식으로 응답하세요:
```json
{{
    "Name_product_short_at_SKU_master": "제품명 (옵션명 기반)",
    "Name_brand_at_SKU_master": "브랜드명",
    "Cost_product_at_SKU_master": {int(calculated_cost) if calculated_cost else '원가 (숫자)'},
    "Price_list_at_SKU_master": {int(calculated_price) if calculated_price else '정가 (숫자)'},
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

            # Override with calculated cost if available (case 1 quantity ratio)
            if calculated_cost is not None:
                gpt_data['Cost_product_at_SKU_master'] = int(calculated_cost)
                gpt_data['Price_list_at_SKU_master'] = int(calculated_price)
                print(f"💰 개수 비율 계산: {base_qty}개 → {new_qty}개 (×{ratio:.2f}) = 원가 {int(calculated_cost)}원")

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

            # From GPT (default to 0 if missing for profit calculation)
            'Name_product_short_at_SKU_master': gpt_data.get('Name_product_short_at_SKU_master'),
            'Name_brand_at_SKU_master': gpt_data.get('Name_brand_at_SKU_master'),
            'Cost_product_at_SKU_master': gpt_data.get('Cost_product_at_SKU_master') or 0,
            'Price_list_at_SKU_master': gpt_data.get('Price_list_at_SKU_master') or 0,

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

            # Ensure cost/price are not None (use 0 for profit calculation)
            cost = record.get('Cost_product_at_SKU_master') or 0
            price = record.get('Price_list_at_SKU_master') or 0

            # Adjust price for case 1 (count) or case 2 (refund)
            if case_type == 1:
                # Calculate based on quantity ratio
                base_name = base_sku.get('Name_product_short_at_SKU_master', '')
                new_name = unmatched_product.get('option_name', '')

                base_qty = self._extract_quantity_from_name(base_name)
                new_qty = self._extract_quantity_from_name(new_name)

                if base_qty and new_qty and base_qty > 0 and cost > 0:
                    ratio = new_qty / base_qty
                    record['Cost_product_at_SKU_master'] = cost * ratio
                    record['Price_list_at_SKU_master'] = price * ratio
                    print(f"💰 개수 비율 계산 (템플릿): {base_qty}개 → {new_qty}개 (×{ratio:.2f}) = 원가 {int(cost * ratio)}원")
                else:
                    # Fallback: keep original
                    record['Cost_product_at_SKU_master'] = cost
                    record['Price_list_at_SKU_master'] = price
            elif case_type == 2:
                # Keep original cost/price for refund items (no discount)
                record['Cost_product_at_SKU_master'] = cost
                record['Price_list_at_SKU_master'] = price

        else:
            # New product - create minimal record with 0 cost/price
            record = {
                'ID_master': new_master_id,
                'Name_product_short_at_SKU_master': unmatched_product.get('option_name'),
                'ID_option_vendor_coupang_at_SKU_master': unmatched_product.get('option_id'),
                'ID_product_sku_coupang_at_SKU_master': unmatched_product.get('product_id'),
                'Category_2p_1_coupang_at_SKU_master': unmatched_product.get('category'),
                'Sales_type_coupang_at_SKU_master': unmatched_product.get('sales_type'),
                'Cost_product_at_SKU_master': 0,
                'Price_list_at_SKU_master': 0,
            }

        return record
