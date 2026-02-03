# cron-job.org를 이용한 정시 실행 설정 가이드

GitHub Actions scheduled workflow는 서버 부하에 따라 수 시간 지연될 수 있습니다.
정확한 시간에 실행하려면 외부 스케줄러를 사용하여 `workflow_dispatch` API를 호출합니다.

---

## 1. GitHub Personal Access Token 생성

### 1.1 토큰 생성 페이지 접속

https://github.com/settings/tokens?type=beta

### 1.2 Fine-grained token 생성

1. **Generate new token** 클릭
2. 설정:
   - **Token name**: `cron-job-workflow-trigger`
   - **Expiration**: 원하는 기간 (최대 1년)
   - **Repository access**: `Only select repositories` → `top10_stocks_sender` 선택
   - **Permissions**:
     - **Actions**: `Read and write` (workflow 실행 권한)

3. **Generate token** 클릭
4. 생성된 토큰 복사 (한 번만 표시됨!)

---

## 2. cron-job.org 설정

### 2.1 회원가입

https://cron-job.org 접속 → 회원가입 (무료)

### 2.2 작업 생성 - 오전 9시 30분 (KST)

1. **CREATE CRONJOB** 클릭
2. 설정:

| 항목 | 값 |
|------|-----|
| **Title** | `Stock Report - Morning (09:30 KST)` |
| **URL** | `https://api.github.com/repos/xxonbang/top10_stocks_sender/actions/workflows/send-telegram.yml/dispatches` |
| **Schedule** | Custom: `30 0 * * 1-5` (UTC) 또는 시간대 선택 후 09:30 |
| **Timezone** | `Asia/Seoul` 선택 시 → `30 9 * * 1-5` |
| **Request Method** | `POST` |

3. **Advanced** 탭:

**Headers** (Add header):
```
Authorization: Bearer ghp_xxxxxxxxxxxxxxxxxxxx
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
```

**Request Body**:
```json
{"ref":"main"}
```

4. **CREATE** 클릭

### 2.3 작업 생성 - 저녁 9시 (KST)

동일한 방법으로 두 번째 작업 생성:

| 항목 | 값 |
|------|-----|
| **Title** | `Stock Report - Evening (21:00 KST)` |
| **URL** | (동일) |
| **Schedule** | Timezone=Asia/Seoul → `0 21 * * 1-5` |

---

## 3. 테스트

### 3.1 cron-job.org에서 수동 실행

작업 목록에서 **Run now** 버튼 클릭

### 3.2 GitHub에서 확인

https://github.com/xxonbang/top10_stocks_sender/actions

`workflow_dispatch` 이벤트로 실행되었는지 확인

---

## 4. 기존 GitHub schedule 비활성화 (선택)

외부 스케줄러만 사용하려면 workflow 파일에서 schedule 제거:

```yaml
on:
  # schedule 주석 처리 또는 삭제
  # schedule:
  #   - cron: '30 0 * * 1-5'
  #   - cron: '0 12 * * 1-5'
  workflow_dispatch:
    inputs:
      skip_news:
        description: '뉴스 수집 건너뛰기'
        required: false
        default: false
        type: boolean
```

---

## 5. 요약

| 시간 (KST) | cron-job.org 설정 (Timezone=Asia/Seoul) |
|------------|----------------------------------------|
| 09:30 월~금 | `30 9 * * 1-5` |
| 21:00 월~금 | `0 21 * * 1-5` |

**API Endpoint**:
```
POST https://api.github.com/repos/xxonbang/top10_stocks_sender/actions/workflows/send-telegram.yml/dispatches
```

**Headers**:
```
Authorization: Bearer {YOUR_GITHUB_TOKEN}
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
```

**Body**:
```json
{"ref":"main"}
```
