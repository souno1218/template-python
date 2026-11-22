# プロジェクト名

<このプロジェクトの目的を1〜2文で>

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

## ドキュメント

知識ドキュメント（提案・判断・実験・設計・参照）は `.okf/` にあります（Open Knowledge Format）。入口は [.okf/index.md](.okf/index.md)、規約は [CLAUDE.md](CLAUDE.md) を参照。
