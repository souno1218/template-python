---
type: Decision
title: OKF を知識ドキュメントの標準にする
description: 知識ドキュメントを Open Knowledge Format v0.3 のバンドルとして .okf/ に置く判断。
tags: [okf, process]
status: stable
generated: { by: "claude/sonnet-5-5", at: "2026-11-22T02:30:00Z" }
sources:
  - id: okf-spec
    resource: https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md
    title: Open Knowledge Format v0.3 specification
---

# 判断

プロジェクトの知識ドキュメント（提案・判断・実験・設計・参照）は、`.okf/` に OKF v0.3 のバンドルとして置く。[^okf-spec]

# 理由

- 通常の Markdown と YAML frontmatter なので、ツールなしで読め、git で差分を追える。
- 出典・信頼度・鮮度を frontmatter に記録でき、AI が書き続けるドキュメントの管理に向く。

# 運用

- `type` は Proposal / Decision / Experiment / Architecture / Reference を標準にする。
- 変更は `tools/okf/validate.py --strict` を通す（pre-commit と CI で実行）。
- 人間の確認を `verified` に記録するのは、本人が id を明示したときだけにする。

[^okf-spec]: Open Knowledge Format v0.3 specification
