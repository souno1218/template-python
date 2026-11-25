# プロジェクト名

<このプロジェクトの目的を1〜2文で>

## テンプレートから作るとき

最初に、次の場所をプロジェクト名に合わせて書き換える。

| 場所 | 書き換え前 | 例 |
|---|---|---|
| `pyproject.toml` の `name` | `project-name` | `my-tool` |
| `pyproject.toml` の `packages` | `["src/project_name"]` | `["src/my_tool"]` |
| フォルダ名 | `src/project_name/` | `src/my_tool/` |
| `tests/test_smoke.py` の import | `import project_name` | `import my_tool` |
| README の題 | `# プロジェクト名` | `# my-tool` |

- `packages` を書き換え忘れても、`uv sync` と `uv build` はエラーにならない。そのまま中身が空のパッケージができて、import だけが失敗する。
- 書き換えたら `uv sync` と `uv run pytest` を実行して、import できることを確かめる。

## セットアップ

```bash
uv sync
uv run pre-commit install
```

## 実行

```bash
# <実行コマンド>
```

## 開発

```bash
uv run ruff check .        # lint
uv run ruff format .       # 整形
uv run ty check            # 型チェック
uv run pytest              # テスト
```

コミットすると、pre-commit が ruff・ty・OKF の検証を実行する。

```bash
# コミット時に ruff が自動修正したら（Failed になり、ファイルが書き換わる）、
# 修正後のファイルを add してからコミットし直す
git add -u
git commit

# "Stashed changes conflicted with hook auto-fixes... Rolling back fixes..." が出たら、
# 未ステージの変更が自動修正とぶつかっている。ファイルは元に戻っているので、
# 未ステージの変更を先に片付けて（add するか stash する）からコミットし直す
git status
```

CI は GitHub Actions（`.github/workflows/ci.yml`）と GitLab CI（`.gitlab-ci.yml`）の両方を用意している。使わないほうは消してよい。

## ドキュメント

知識ドキュメント（提案・判断・実験・設計・参照）は `.okf/` にあります（Open Knowledge Format）。入口は [.okf/index.md](.okf/index.md)、AI エージェント向けの規約は [AGENTS.md](AGENTS.md) を参照（`CLAUDE.md` はこれを読み込むだけ）。
