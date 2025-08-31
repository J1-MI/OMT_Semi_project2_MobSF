# MobSF 기본 가이드 (순정 상태 기준)

이 문서는 'MobSF (Mobile Security Framework)' 공식 문서와 GitHub README를 기반으로 정리한 가이드.
(기본 설치, 사용법, REST API 활용법, 그리고 보안 운영 모범 사례까지 포함)

---

1. 설치 & 실행 (가장 쉬운 방법: Docker)

```bash
# 이미지 받기
docker pull opensecurity/mobile-security-framework-mobsf:latest

# 실행 (로컬 8000 포트 → 컨테이너 8000 포트)
docker run -it --rm -p 8000:8000 opensecurity/mobile-security-framework-mobsf:latest
접속: http://localhost:8000

기본 로그인: mobsf / mobsf (최초 실행 시 기본 계정)

참고: MobSF GitHub 공식 README에도 동일한 Docker 명령과 설명이 제공됩니다.

2. 초기 로그인 & 기본(순정) 상태에서 알아둘 것
계정: 기본 mobsf/mobsf → 반드시 비밀번호 변경 권장 (실서비스에는 부적합)

포트: 기본 8000번 포트에서 GUI 제공

분석 종류

정적 분석 (Static): APK/IPA/APPX/소스코드 업로드 후 자동 취약점 분석

동적 분석 (Dynamic): 앱을 에뮬레이터/실기기에 실행하여 런타임 동작 및 트래픽 분석

3. 기본 사용 흐름 (정적 분석)
로그인

파일 업로드 (APK, IPA 등)

리포트 확인 및 다운로드

웹 UI에서 매니페스트, 권한, 하드코딩 시크릿, 취약점 매핑 등의 상세 리포트를 확인할 수 있습니다.

4. 기본 사용 흐름 (동적 분석 - Android 예시)
MobSF 실행 후 Dynamic Analyzer 메뉴 진입

에뮬레이터/디바이스 연결 (ADB 활성화 필요)

안내에 따라 프록시 및 인증서 설정

앱 실행 및 조작 → 트래픽/런타임 이벤트 수집

팁: 프록시 설정이 맞지 않으면 settings.py에서 PROXY_IP와 PROXY_PORT 값을 확인.

Genymotion 사용 시 반드시 ADB Enable 설정 필요.

5. REST API (자동화 / CI 용)
MobSF는 REST API를 통해 업로드, 분석, 리포트 다운로드를 자동화할 수 있음.

API 키 확인
웹 UI → 우측 상단 Profile/Settings → API Key 확인

주요 엔드포인트
엔드포인트	설명
POST /api/v1/upload	파일 업로드
POST /api/v1/scan	업로드된 파일 분석 실행
POST /api/v1/report_json	JSON 리포트 다운로드
POST /api/v1/report_pdf	PDF 리포트 다운로드

예시
bash
코드 복사
# 1) 파일 업로드
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "X-MobSF-API-Key: <YOUR_API_KEY>" \
  -F "file=@/path/to/app.apk"

# 2) 스캔 실행
curl -X POST "http://localhost:8000/api/v1/scan" \
  -H "X-MobSF-API-Key: <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"scan_type":"apk","file_name":"app.apk","hash":"<HASH>"}'

# 3) JSON 리포트 다운로드
curl -X POST "http://localhost:8000/api/v1/report_json" \
  -H "X-MobSF-API-Key: <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"hash":"<HASH>"}' -o report.json
6. 순정 기준 기본 설정 요약
계정/인증: mobsf/mobsf → 즉시 변경, 외부 서비스 연동 시 리버스 프록시 및 인증 추가

포트/바인딩: 기본 8000 포트 사용, 내부망 또는 방화벽으로 접근 제한 권장

네트워크 설정: 프록시 및 식별자(ANALYZER_IDENTIFIER) 환경에 맞춰 설정

분석 대상 포맷: APK, XAPK, APKS, JAR, AAR, ZIP, IPA 등

7. 보안 운영 모범사례
비밀번호 변경: 설치 직후 즉시 변경, 관리자 계정은 분리 운영

리버스 프록시 배치: RP4MobSF 활용, SSL/TLS와 Basic Auth 적용

네트워크 격리: 내부망 전용 운영, 방화벽 포트 최소화

API 키 보호: 환경 변수나 Vault에 저장, 코드에 직접 노출 금지

8. CI/CD & CLI 확장
mobsfscan: SAST 전용 스캐너로, .mobsf 설정 파일을 통해 규칙 및 제외 경로 관리 가능

클라우드 연동: AWS EC2, GitLab, Jenkins, Bitrise 등과 연계해 자동 스캔 및 리포트 생성 가능

9. 동적 분석 셋업 팁
ADB 허용: Genymotion 등 가상 환경은 반드시 ADB Enable

프록시 설정 확인: MobSF와 에뮬레이터 간 IP/포트 일치 여부 확인

장치 식별 수동 지정: 감지가 안 될 경우 ANALYZER_IDENTIFIER='IP:5555' 수동 입력

출처 및 라이선스
원문: MobSF GitHub
License: GNU GPL v3.0


