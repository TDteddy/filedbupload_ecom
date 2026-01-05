"""
GPT-based analyzer for Coupang 2P product classification.
Determines whether unmatched products are:
1. Count-modified auto-generated items (same package, different quantity)
2. Refund/return resales
3. New products (including package/size changes)
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class CoupangProductAnalyzer:
    """Analyzes Coupang 2P products using GPT to classify and match with existing SKUs."""

    def __init__(self):
        """Initialize OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def analyze_product(self, unmatched_product, existing_skus):
        """
        Analyze an unmatched product and classify it.

        Args:
            unmatched_product: Dict with product info
                - option_id: 옵션 ID
                - option_name: 옵션명
                - product_id: 등록상품 ID
                - category: 카테고리
                - sales_type: 판매방식

            existing_skus: List of dicts with existing SKU_master data
                - ID_master: Master ID
                - Name_product_short_at_SKU_master: 제품명
                - Name_brand_at_SKU_master: 브랜드
                - ID_option_vendor_coupang_at_SKU_master: 쿠팡 옵션 ID
                - Category_2p_1_coupang_at_SKU_master: 카테고리
                - Cost_product_at_SKU_master: 원가
                - Price_list_at_SKU_master: 정가

        Returns:
            Dict with:
                - case_type: int (1: 개수변경(같은패키지), 2: 환불재판매, 3: 신규상품(용량변경포함))
                - base_master_id: str or None (기초가 되는 ID_master, 케이스 3이면 None)
                - confidence: float (0-1)
                - reasoning: str (판단 근거)
        """
        prompt = self._build_analysis_prompt(unmatched_product, existing_skus)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """당신은 이커머스 상품 데이터 분석 전문가입니다.
쿠팡 2P 판매 데이터에서 새로 나타난 옵션 ID를 분석하여 다음 3가지 케이스 중 하나로 분류하세요:

**케이스 1 (개수변경 자동생성)**: 쿠팡이 같은 패키지의 상품을 개수만 변경하여 자동 생성한 경우
- 특징: **같은 용량/사이즈**의 제품을 **개수만 변경** (예: "500ml 1병" → "500ml 2병", "10개입" → "20개입")
- 같은 브랜드, 같은 카테고리, **같은 패키지 크기**
- 원가는 개수에 정확히 비례 (2배수량 = 2배원가)
- ⚠️ 중요: 용량/사이즈가 바뀌면 (예: "500ml" → "1L") 이건 케이스 3입니다!
- ⚠️ base_master_id 선택: 같은 상품의 여러 개수 옵션이 있다면, **가장 작은 개수(1개, 1병 등 기본 단위)**를 base로 선택하세요!

**케이스 2 (환불재판매)**: 환불/반품된 상품을 재판매하는 경우
- 특징: "환불", "반품", "재판매", "리퍼", "중고", "아울렛" 등의 키워드 포함
- 또는 옵션명에 "B급", "C급", "하자" 등이 있음
- 기존 제품과 거의 동일하지만 특수 판매 형태

**케이스 3 (신규상품)**: 완전히 새로운 상품 또는 패키지가 변경된 경우
- 특징: 기존 DB에 유사한 상품이 없음
- 새로운 브랜드이거나 완전히 다른 제품군
- **용량/사이즈가 바뀐 경우도 여기 해당** (예: "500ml" → "1L", "100g" → "200g")
  → 패키지가 달라지므로 원가 구조가 다름

반드시 JSON 형식으로만 응답하세요."""
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

            result = json.loads(response.choices[0].message.content)

            # Validate and normalize result
            return self._validate_result(result)

        except Exception as e:
            print(f"❌ GPT 분석 실패: {e}")
            # Fallback: 신규상품으로 처리
            return {
                "case_type": 3,
                "base_master_id": None,
                "confidence": 0.0,
                "reasoning": f"GPT 분석 실패로 신규상품으로 처리: {str(e)}"
            }

    def _build_analysis_prompt(self, unmatched_product, existing_skus):
        """Build the analysis prompt for GPT."""
        # Limit existing SKUs to most relevant ones (max 20)
        relevant_skus = self._find_relevant_skus(unmatched_product, existing_skus, limit=20)

        prompt = f"""
## 분석 대상 (매칭되지 않은 신규 옵션)
- 옵션 ID: {unmatched_product.get('option_id', 'N/A')}
- 옵션명: {unmatched_product.get('option_name', 'N/A')}
- 등록상품 ID: {unmatched_product.get('product_id', 'N/A')}
- 카테고리: {unmatched_product.get('category', 'N/A')}
- 판매방식: {unmatched_product.get('sales_type', 'N/A')}

## 기존 SKU_master 데이터 (유사도 높은 순)
"""

        if relevant_skus:
            for idx, sku in enumerate(relevant_skus, 1):
                prompt += f"""
### [{idx}] ID_master: {sku.get('ID_master', 'N/A')}
- 제품명: {sku.get('Name_product_short_at_SKU_master', 'N/A')}
- 브랜드: {sku.get('Name_brand_at_SKU_master', 'N/A')}
- 쿠팡 옵션 ID: {sku.get('ID_option_vendor_coupang_at_SKU_master', 'N/A')}
- 카테고리: {sku.get('Category_2p_1_coupang_at_SKU_master', 'N/A')}
- 원가: {sku.get('Cost_product_at_SKU_master', 'N/A')}
- 정가: {sku.get('Price_list_at_SKU_master', 'N/A')}
"""
        else:
            prompt += "\n(기존 데이터 없음 - 신규상품일 가능성 높음)\n"

        prompt += """

## 요청사항
위 정보를 바탕으로 분석 대상이 어떤 케이스에 해당하는지 판단하고, 다음 JSON 형식으로 응답하세요:

```json
{
    "case_type": 1 또는 2 또는 3,
    "base_master_id": "기초가 되는 ID_master (케이스 3이면 null)",
    "confidence": 0.0~1.0 사이의 확신도,
    "reasoning": "판단 근거를 한글로 상세히 설명"
}
```

예시:
- 개수변경: {"case_type": 1, "base_master_id": "42", "confidence": 0.95, "reasoning": "기존 '500ml 1병' 제품과 브랜드/카테고리 동일하며 같은 패키지의 '500ml 2병'으로 개수만 2배 증가"}
- 환불재판매: {"case_type": 2, "base_master_id": "42", "confidence": 0.9, "reasoning": "옵션명에 '리퍼' 키워드 포함, 기존 제품과 동일"}
- 신규상품(브랜드): {"case_type": 3, "base_master_id": null, "confidence": 0.85, "reasoning": "기존 DB에 해당 브랜드나 유사 제품 없음"}
- 신규상품(용량변경): {"case_type": 3, "base_master_id": null, "confidence": 0.90, "reasoning": "기존 '500ml' 제품이 있으나 신규는 '1L'로 패키지 용량이 변경되어 신규 상품으로 분류"}
"""

        return prompt

    def _find_relevant_skus(self, unmatched_product, existing_skus, limit=20):
        """
        Find most relevant existing SKUs based on similarity.
        Simple implementation using category and product name matching.
        """
        if not existing_skus:
            return []

        option_name = unmatched_product.get('option_name', '').lower()
        category = unmatched_product.get('category', '').lower()

        # Score each SKU
        scored_skus = []
        for sku in existing_skus:
            score = 0

            # Category match (highest priority)
            sku_category = str(sku.get('Category_2p_1_coupang_at_SKU_master', '')).lower()
            if category and sku_category and category in sku_category:
                score += 10

            # Product name similarity
            sku_name = str(sku.get('Name_product_short_at_SKU_master', '')).lower()
            if sku_name and option_name:
                # Simple word overlap
                option_words = set(option_name.split())
                sku_words = set(sku_name.split())
                common_words = option_words & sku_words
                score += len(common_words)

            scored_skus.append((score, sku))

        # Sort by score and return top N
        scored_skus.sort(key=lambda x: x[0], reverse=True)
        return [sku for score, sku in scored_skus[:limit] if score > 0]

    def _validate_result(self, result):
        """Validate and normalize GPT result."""
        # Ensure required fields exist
        if 'case_type' not in result:
            result['case_type'] = 3  # Default to new product

        # Validate case_type
        if result['case_type'] not in [1, 2, 3]:
            result['case_type'] = 3

        # Ensure confidence is float between 0 and 1
        if 'confidence' not in result:
            result['confidence'] = 0.5
        else:
            try:
                result['confidence'] = float(result['confidence'])
                result['confidence'] = max(0.0, min(1.0, result['confidence']))
            except:
                result['confidence'] = 0.5

        # Ensure reasoning exists
        if 'reasoning' not in result:
            result['reasoning'] = "분석 완료"

        # Handle base_master_id
        if 'base_master_id' not in result:
            result['base_master_id'] = None
        elif result['case_type'] == 3:
            result['base_master_id'] = None  # New products don't have base

        return result
