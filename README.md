# CBAM 탄소 비용 리스크 대시보드

EU CBAM(탄소국경조정제도) 시행에 대비해, 품목별 탄소 비용 리스크 등급을 산출하고
기업이 직접 비용을 시뮬레이션해볼 수 있는 Streamlit 대시보드입니다.
2026 무역통계 활용분석 경진대회 프로젝트입니다.

## 데모 영상

- 대시보드 시연: https://youtu.be/Ee0iQxsjiSw

## 파이프라인 (notebook/)

1. `KAU_EUA_가격산출.ipynb` — 한국(KAU)·유럽(EUA) 배출권 가격 산출
2. `마스터테이블_구축_및_스케일링.ipynb` — 관세청 수출입 데이터 + 배출권 가격 통합 마스터테이블 구축
3. `피처별_예측_및_리스크스코어_산출.ipynb` — 품목별 리스크 스코어 산출 및 2026년 예측
4. `보고서_시각화.ipynb` — 최종 보고서용 시각화

## 대시보드 (dashboard/)

파이프라인 결과물(가공된 마스터테이블/리스크 분석 결과)을 바탕으로 만든 Streamlit 앱입니다.

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

## 대시보드 배포

https://cbam-risk-dashboard-d6qljdz88xcwta3zwg2yhi.streamlit.app/

## 포함하지 않은 것

- 관세청 원본 수출입 통계 원본 CSV(64MB) — 대시보드에는 이미 가공된 소용량 버전(`dashboard/data/`)을 사용

## 기술 스택

Python, Pandas, Streamlit, Plotly
