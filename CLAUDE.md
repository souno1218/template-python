# プロジェクトの規約

## 開発環境

- Python は uv で管理する（`uv sync`）。lint と整形は ruff、型検査は ty、テストは pytest。
- コミット前（pre-commit）と CI で、`uv run ruff check .` / `uv run ruff format --check .` / `uv run ty check` / `uv run pytest` / OKF の検証を実行する。変更を終える前に自分でも実行して通すこと。
- 最初に `pyproject.toml` の `name`、`src/project_name/` の名前、README の題を、プロジェクト名に合わせて直す。

## 知識ドキュメントは OKF で書く

このプロジェクトの知識ドキュメントは `.okf/` の Open Knowledge Format (OKF) v0.3 バンドルに置く。検討や実装を始める前に、必ず次を読むこと。

1. `.okf/index.md` と、関係する種別の `index.md`
2. 関係する Decision（過去の判断と理由）

### type の標準（これ以外を使うときは理由を Decision に残す）

| type | 置き場所 | 内容 |
|---|---|---|
| Proposal | `.okf/proposals/` | 施策の開始前に人間が承認する提案書 |
| Decision | `.okf/decisions/` | 採用・不採用などの判断と理由 |
| Experiment | `.okf/experiments/` | 実験の設定・結果・考察 |
| Architecture | `.okf/architecture/` | 構成・設計・モデル構造の説明 |
| Reference | `.okf/references/` | 外部資料・論文・仕様の参照メモ |

### 書き方

- 1ファイル1コンセプト。frontmatter に非空の `type` を必ず書く。雛形は `tools/okf/templates/` にある。
- `generated: { by: "claude/<model>", at: "<UTC の日時>" }` を自分の名義で書く。意味が変わらない整形では更新しない。
- 出典のない事実は書かない。`sources` に出典を書き、主張には脚注（ラベルは `sources[].id`）を付ける。
- `verified` は、人間が確認して自分の id（`human:<id>`）を明示したときだけ追記する。推測で付けない。
- 既存ファイルを更新するときは、他者が書いたキー・`verified` 履歴・本文を保つ。
- パス系フィールド（`resource` など）は先頭 `/` で書く。本文のリンクはファイルからの相対パスで書く。
- 変更したら、そのディレクトリの `index.md` と `.okf/log.md`（日付の新しい順）を更新する。
- 終わる前に `python3 tools/okf/validate.py .okf --strict` を実行し、エラーと警告を直す。

### 人間の承認

- Proposal は人間の承認を得てから実行に移す。承認後に Decision を書く。
- 勝手に既存ドキュメントを書き換えない。書き直しは提案して承認を得てから行う。
