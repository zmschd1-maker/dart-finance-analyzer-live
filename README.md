# DART 재무제표 분석기 — 라이브(Vercel) 배포판

원본 `zmschd1-maker/dart-finance-analyzer` 의 `app.py`(표준 라이브러리
`http.server` 기반)를 **UI·기능 그대로** Vercel Python 서버리스에서 돌도록 감싼 것입니다.

## 라이브

- 사이트: https://dart-finance-analyzer-live.vercel.app
- Vercel 프로젝트: `zmschd1-maker/dart-finance-analyzer-live` (Hobby · 서울 리전 icn1)

## 구조

| 파일 | 설명 |
| --- | --- |
| `app_core.py` | 원본 `app.py` 와 동일. 서버리스 환경에 맞춰 상장사 목록 로딩만 보강 (`/tmp` 캐시 + 저장소 번들 스냅샷) |
| `wsgi.py` | Vercel WSGI 엔트리포인트. 원본 `Handler` 를 그대로 호출하고 응답만 WSGI 로 변환 |
| `corp_list.json.gz` | DART 상장사 목록 스냅샷 (콜드 스타트 시 즉시 검색 가능하도록 번들) |
| `pyproject.toml` | 의존성 없음(표준 라이브러리만) + `[tool.vercel] entrypoint` |
| `vercel.json` | 서울 리전(icn1), 함수 실행 시간 60초 |

## 환경변수 (Vercel 프로젝트 설정에 등록)

`DART_API_KEY`, `KIS_APP_KEY`, `KIS_APP_SECRET`, `NAVER_CLIENT_ID`,
`NAVER_CLIENT_SECRET`, `GEMINI_API_KEY`

키는 소스코드에 절대 넣지 않습니다. 로컬 실행은 저장소 밖 `.env` 를 만들어
`set -a && . ./.env && set +a && python app_core.py` 로 확인합니다.

## 로컬 실행 (원본과 동일)

```bash
python app_core.py   # http://localhost:8787
```
