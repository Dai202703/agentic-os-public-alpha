# Agentic OS 日本語ガイド

Agentic OS(AOS) は、特定の AI ベンダーに依存しない local-first の context と memory システムです。Codex、Claude Code、Gemini、ChatGPT などが読む provider instruction ファイルを生成しながら、重要な作業文脈や意思決定はユーザーのローカル OS home に保存します。

基本の考え方はシンプルです。自分の仕事に合うカテゴリを作り、AI に覚えておいてほしい情報を memory として保存し、使う provider 向けに compile します。

## 5分で開始

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

Windows PowerShell では、インストール行を次のように置き換えます。

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

コマンドラインに慣れていない場合は、まず [Install AOS For Beginners](install-for-beginners.md) を読んでください。

## カテゴリは自分で決める

AOS は固定された業務カテゴリを押し付けません。`aos link-project --id` に渡す値が、あなたの作業カテゴリになります。

例:

```bash
aos link-project --project-root /tmp/aos-book --id book-draft --name "Book Draft" --provider chatgpt
aos link-project --project-root /tmp/aos-class --id biology-101 --name "Biology 101" --provider gemini
aos link-project --project-root /tmp/aos-case --id case-research --name "Case Research" --provider claude
```

カテゴリ ID には英数字、ハイフン、アンダースコアを使ってください。スペース、スラッシュ、顧客名、秘密情報は避けるのが安全です。

## Memory の使い方

Memory は、セッションの要約、意思決定、次の作業、成果物の場所など、次回の AI セッションでも引き継ぎたい情報を保存する場所です。

```bash
aos memory template session --project-id first-project
aos memory template decision --project-id first-project
aos memory list --project-id first-project
aos memory search "provider compile" --project-id first-project
```

新しい memory を追加したあと、その内容を AI ツールに反映したい場合は、もう一度 compile します。

```bash
aos compile codex --project-root /tmp/aos-first-project
```

詳しい流れは [Memory Workflows](memory-workflows.md) を参照してください。

## Provider 出力

AOS は同じローカル context を、複数の AI ツールが読めるファイルに変換します。

- Codex: `AGENTS.md`
- Claude Code: `CLAUDE.md`
- Gemini: `GEMINI.md`
- ChatGPT: `.agentic-os/chatgpt-project-instructions.md`

これらは生成ファイルです。長く手作業で編集するより、context と memory を更新してから `aos compile` で再生成する運用が安定します。

## 公開配布とプライバシー

公開パッケージには、個人 identity、client context、API key、generated provider output、live OS home を含めないでください。公開前には次のチェックを通します。

```bash
aos distribution-check --repo-root . --json
aos public-audit --repo-root . --json
aos release-check --repo-root . --json
```

公開リリース担当者は [Public Release](public-release.md) と [Distribution](distribution.md) の最終 gate も確認してください。
