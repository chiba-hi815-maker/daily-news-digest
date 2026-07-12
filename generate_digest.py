name: Daily News Digest

on:
  schedule:
    # UTC 21:00 = JST 6:00 (毎朝6時に実行)
    - cron: "0 21 * * *"
  workflow_dispatch: {}  # Actionsタブから手動実行するためのトリガー

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: リポジトリを取得
        uses: actions/checkout@v4

      - name: Pythonをセットアップ
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: ダイジェストを生成
        run: python generate_digest.py

      - name: 生成結果をコミット
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/index.html
          git diff --quiet && git diff --staged --quiet || git commit -m "Update daily digest"
          git push
