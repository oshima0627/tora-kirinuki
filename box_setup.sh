#!/usr/bin/env bash
# box（共有Linux）用: 毎回これを source してから日次コマンドを叩く。
#   source box_setup.sh
# venv 有効化・deno を PATH に・POトークンサーバ(bgutil 1.3.1, :4416)が落ちていれば起動。
cd "$(dirname "${BASH_SOURCE[0]}")"
export PATH="$HOME/.deno/bin:$PATH"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt bgutil-ytdlp-pot-provider==1.3.1 "yt-dlp[default]"; }
source .venv/bin/activate
if ! curl -fsS --max-time 3 http://127.0.0.1:4416/ping >/dev/null 2>&1; then
  if [ ! -f "$HOME/bgutil-ytdlp-pot-provider/server/build/main.js" ]; then
    git clone -q --depth 1 --branch 1.3.1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git "$HOME/bgutil-ytdlp-pot-provider"
    (cd "$HOME/bgutil-ytdlp-pot-provider/server" && npm install --silent && npx tsc)
  fi
  (cd "$HOME/bgutil-ytdlp-pot-provider/server" && setsid nohup node build/main.js >/tmp/bgutil-pot.log 2>&1 &)
  sleep 3
fi
curl -fsS --max-time 3 http://127.0.0.1:4416/ping && echo
