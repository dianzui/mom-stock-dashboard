#!/bin/bash
# 每天收盘后自动生成股票看板并推送到 GitHub
# 由 launchd 在 16:30 调用；也可手动双击运行
set -u
export PATH="$HOME/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
export TZ=Asia/Shanghai

PROJ="$HOME/Desktop/Hermes工作区/20261026-母亲股票看板"
LOG="$PROJ/data/run.log"
mkdir -p "$PROJ/data"

# 周末不跑
DOW=$(date +%u)
if [ "$DOW" -gt 5 ]; then
  echo "[$(date '+%F %T')] 周末，跳过" >> "$LOG"
  exit 0
fi

cd "$PROJ" || exit 1
echo "[$(date '+%F %T')] ===== 开始 =====" >> "$LOG"

/usr/bin/python3 build.py        >> "$LOG" 2>&1 || { echo "[$(date '+%F %T')] build 失败" >> "$LOG"; exit 1; }
/usr/bin/python3 gather_watch.py >> "$LOG" 2>&1
/usr/bin/python3 render.py       >> "$LOG" 2>&1 || { echo "[$(date '+%F %T')] render 失败" >> "$LOG"; exit 1; }

cp dashboard.html index.html
git add index.html >> "$LOG" 2>&1
if git diff --staged --quiet; then
  echo "[$(date '+%F %T')] 内容无变化，不提交" >> "$LOG"
else
  git -c user.name="dianzui" -c user.email="dianzui@users.noreply.github.com" \
      commit -q -m "自动更新 $(date '+%Y-%m-%d %H:%M')" >> "$LOG" 2>&1
  git push -q origin main >> "$LOG" 2>&1 && echo "[$(date '+%F %T')] 已推送" >> "$LOG"
fi
echo "[$(date '+%F %T')] ===== 完成 =====" >> "$LOG"
