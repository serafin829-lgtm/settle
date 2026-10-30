#!/usr/bin/env bash
# Regenera video/settle_demo.mp4 sin créditos: app en MOCK, captura headless, TTS edge-tts (fallback espeak-ng), ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"; V=$PWD; APP=$(dirname "$V"); W=$V/build; rm -rf "$W"; mkdir -p "$W"
VENV=${VENV:-/workspace/.vidvenv}
[ -x "$VENV/bin/python" ] || { python3 -m venv "$VENV"; "$VENV/bin/pip" install -q playwright edge-tts; "$VENV/bin/python" -m playwright install chromium; }
PY=$VENV/bin/python
calc(){ awk "BEGIN{printf \"%.3f\", $1}"; }
ts(){ awk -v t="$1" 'BEGIN{h=int(t/3600);m=int((t-h*3600)/60);s=t-h*3600-m*60;x=sprintf("%02d:%02d:%06.3f",h,m,s);sub(/\./,",",x);print x}'; }
( cd "$APP" && exec env -u PAYPAL_CLIENT_ID -u PAYPAL_CLIENT_SECRET SETTLE_ENV_FILE=/dev/null PORT=8799 DB_PATH="$W/demo.db" python3 run.py >"$W/app.log" 2>&1 ) & APID=$!
trap 'kill $APID 2>/dev/null || true' EXIT
for i in $(seq 30); do curl -s -o /dev/null http://127.0.0.1:8799/ && break; sleep 0.5; done
"$PY" capturar.py "$W"
: > "$W/list.txt"; : > "$W/subs.srt"; T=0; n=0
while IFS='|' read -r S TXT; do
  "$VENV/bin/edge-tts" --voice en-US-AndrewNeural --rate=-5% --text "$TXT" --write-media "$W/$S.mp3" 2>/dev/null || espeak-ng -v en-us -s 160 -w "$W/$S.mp3" "$TXT"
  D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$W/$S.mp3"); D=$(calc "$D+1.8")
  IMGS=($(ls "$W"/${S}_*.png)); K=${#IMGS[@]}; PER=$(calc "$D/$K")
  : > "$W/$S.imgs"; for I in "${IMGS[@]}"; do echo "file '$I'" >>"$W/$S.imgs"; echo "duration $PER" >>"$W/$S.imgs"; done; echo "file '${IMGS[-1]}'" >>"$W/$S.imgs"
  ffmpeg -nostdin -v error -y -f concat -safe 0 -i "$W/$S.imgs" -i "$W/$S.mp3" -filter_complex "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:white,fps=30,format=yuv420p[v];[1:a]apad,aresample=44100[a]" -map "[v]" -map "[a]" -t "$D" -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 160k "$W/$S.mp4"
  echo "file '$W/$S.mp4'" >>"$W/list.txt"
  n=$((n+1)); E=$(calc "$T+$D-0.3"); printf '%d\n%s --> %s\n%s\n\n' $n "$(ts $T)" "$(ts $E)" "$TXT" >>"$W/subs.srt"; T=$(calc "$T+$D")
done < narracion.txt
ffmpeg -nostdin -v error -y -f concat -safe 0 -i "$W/list.txt" -vf "subtitles=$W/subs.srt:force_style='FontName=DejaVu Sans,FontSize=10,Outline=2,BorderStyle=3,BackColour=&H80000000,MarginV=18'" -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 160k -movflags +faststart settle_demo.mp4
ffprobe -v error -show_entries format=duration:stream=width,height -of default=nw=1 settle_demo.mp4
