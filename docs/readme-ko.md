# Agentic OS 한국어 가이드

Agentic OS(AOS)는 특정 AI 공급처에 종속되지 않는 로컬 우선 context 및 memory 시스템입니다. Codex, Claude Code, Gemini, ChatGPT 같은 도구가 각자 읽는 provider instruction 파일을 생성하면서도, 중요한 작업 맥락과 결정 기록은 사용자의 로컬 OS home에 보관합니다.

핵심 개념은 단순합니다. 자신에게 맞는 카테고리를 만들고, 반복해서 기억해야 할 정보를 memory로 저장한 뒤, 사용하는 AI 도구에 맞는 provider 파일을 compile합니다.

## 5분 시작

```bash
git clone https://github.com/Dai202703/agentic-os-public-alpha.git
cd agentic-os-public-alpha
sh scripts/install.sh
aos init
mkdir -p /tmp/aos-first-project
aos link-project --project-root /tmp/aos-first-project --id first-project --name "First Project" --provider codex
aos memory add session --project-id first-project --title "First memory" --summary "Use AOS to keep reusable AI context outside one vendor."
aos compile codex --project-root /tmp/aos-first-project
```

Windows PowerShell에서는 설치 줄을 아래처럼 바꿉니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

명령어 사용이 익숙하지 않다면 [Install AOS For Beginners](install-for-beginners.md)를 먼저 보세요.

## 내 카테고리는 내가 정합니다

AOS는 고정된 업무 분류를 강요하지 않습니다. `aos link-project --id`에 넣는 값이 곧 내 작업 카테고리입니다.

예시:

```bash
aos link-project --project-root /tmp/aos-book --id book-draft --name "Book Draft" --provider chatgpt
aos link-project --project-root /tmp/aos-class --id biology-101 --name "Biology 101" --provider gemini
aos link-project --project-root /tmp/aos-case --id case-research --name "Case Research" --provider claude
```

카테고리 ID에는 영문자, 숫자, 하이픈, 언더스코어를 사용하세요. 공백, 슬래시, 고객 실명, 비밀 정보는 넣지 않는 것이 안전합니다.

## Memory 사용 방식

Memory는 세션 요약, 의사결정, 다음 작업, 산출물 경로처럼 다음 AI 세션에서도 이어져야 하는 정보를 저장하는 곳입니다.

```bash
aos memory template session --project-id first-project
aos memory template decision --project-id first-project
aos memory list --project-id first-project
aos memory search "provider compile" --project-id first-project
```

새 memory를 추가한 뒤 AI 도구가 그 내용을 읽게 하려면 다시 compile합니다.

```bash
aos compile codex --project-root /tmp/aos-first-project
```

자세한 흐름은 [Memory Workflows](memory-workflows.md)를 참고하세요.

## Provider 출력

AOS는 같은 로컬 context를 여러 AI 도구가 읽을 수 있는 파일로 변환합니다.

- Codex: `AGENTS.md`
- Claude Code: `CLAUDE.md`
- Gemini: `GEMINI.md`
- ChatGPT: `.agentic-os/chatgpt-project-instructions.md`

이 파일들은 생성물입니다. 직접 오래 수정하기보다 context와 memory를 업데이트한 뒤 `aos compile`로 다시 생성하는 방식이 안정적입니다.

## 공개 배포와 개인정보

공개 패키지에는 개인 identity, client context, API key, generated provider output, live OS home이 들어가지 않아야 합니다. 공개 전에는 아래 검사를 통과해야 합니다.

```bash
aos distribution-check --repo-root . --json
aos public-audit --repo-root . --json
aos release-check --repo-root . --json
```

공개 릴리스 담당자는 [Public Release](public-release.md)와 [Distribution](distribution.md)의 최종 gate를 함께 확인하세요.
