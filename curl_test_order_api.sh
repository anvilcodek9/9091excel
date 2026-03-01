#!/bin/bash
# 조건형 상품 주문 상세 내역 조회 API 테스트
# 사용법: YOUR_ACCESS_TOKEN 부분을 실제 토큰으로 바꾼 뒤 실행

TOKEN=""

# API 제한: from ~ to 는 최대 24시간 차이. 최신 23시간 구간(KST) 사용
FROM=$(python3 -c "from datetime import datetime, timedelta, timezone; t=datetime.now(timezone(timedelta(hours=9)))-timedelta(hours=23); print(t.isoformat(timespec='milliseconds'))")
TO=$(python3 -c "from datetime import datetime, timedelta, timezone; print(datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='milliseconds'))")

curl -G "https://api.commerce.naver.com/external/v1/pay-order/seller/product-orders" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  --data-urlencode "rangeType=PAYED_DATETIME" \
  --data-urlencode "from=${FROM}" \
  --data-urlencode "to=${TO}" \
  --data-urlencode "paymentStatus=PAYED" \
  -w "\n\nHTTP_CODE:%{http_code}\n" \
  -s | tee /tmp/naver_order_response.json
