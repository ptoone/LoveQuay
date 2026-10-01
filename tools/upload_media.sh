#!/usr/bin/env bash
# Push the media originals to Cloudflare R2.
#
#   bash tools/upload_media.sh            # upload
#   bash tools/upload_media.sh --list     # just print what would go
#   bash tools/upload_media.sh --dry-run  # go through the motions, write nothing
#
# On Windows use tools/upload_media.ps1 instead — same thing, natively.
#
# media.html links to these; it does not host them. They are too big for GitHub
# Pages, which rejects any file over 100 MB and caps a whole site at 1 GB.
#
# Every file is named explicitly below rather than matched by a filter. rclone's
# --include / --exclude precedence is easy to get subtly wrong — an --exclude
# alongside an --include was silently losing here — and with a handful of files
# an explicit list is both safer and self-documenting.
#
# ---------------------------------------------------------------------------
# One-time setup
# ---------------------------------------------------------------------------
#  1. Cloudflare dashboard -> R2 -> Create bucket, named `lovequay-media`.
#  2. That bucket -> Settings -> Public access -> Connect a custom domain,
#     enter `media.lovequay.com`. Cloudflare adds the DNS record for you.
#     (Do not use the r2.dev URL in production — it is rate limited.)
#  3. R2 -> Manage API tokens -> Create token, Object Read & Write.
#  4. Configure rclone once. Nothing is stored in this repo; rclone keeps it in
#     its own config file.
#
#       rclone config create lovequay-r2 s3 \
#         provider=Cloudflare \
#         access_key_id=<ACCESS_KEY> \
#         secret_access_key=<SECRET> \
#         endpoint=https://<ACCOUNT_ID>.r2.cloudflarestorage.com \
#         acl=private
# ---------------------------------------------------------------------------
set -euo pipefail

SRC="${SRC:-C:/Users/p/Downloads/PeterStreetBasin2026sep06-1-001}"
REMOTE="lovequay-r2"
BUCKET="lovequay-media"

# "inline" is served as-is so it can be previewed. "download" gets a
# Content-Disposition header so a click saves it — the HTML download attribute
# is ignored on cross-origin links, and without this a click on the 3840 GIF
# would ask the browser to paint 780 MB of animation in a tab.
FILES=(
  "inline:LoveQuay-splat-transparent-640.gif"
  "inline:LoveQuay-splat-transparent-1920.webm"
  "inline:LoveQuay-splat-transparent-1280.webp"
  "download:LoveQuay-splat-transparent-1920.gif"
  "download:LoveQuay-splat-transparent-3840.gif"
  "download:LoveQuay_2026-09-17_rc0011b_merge001_20MCompColor_dbros.mp4"
)

MODE="upload"
case "${1:-}" in
  --list)    MODE="list" ;;
  --dry-run) MODE="dry" ;;
  "")        ;;
  *)         echo "unknown option: $1" >&2; exit 2 ;;
esac

command -v rclone >/dev/null 2>&1 || { echo "rclone not found." >&2; exit 1; }
[ -d "$SRC" ] || { echo "source folder not found: $SRC" >&2; exit 1; }

printf '\n%-60s %12s  %s\n' "FILE" "SIZE" "SERVED AS"
total=0
for entry in "${FILES[@]}"; do
  how="${entry%%:*}"; name="${entry#*:}"
  if [ -f "$SRC/$name" ]; then
    bytes=$(wc -c < "$SRC/$name")
    total=$((total + bytes))
    printf '%-60s %9d MB  %s\n' "$name" "$((bytes / 1048576))" "$how"
  else
    printf '%-60s %12s  MISSING\n' "$name" "-"
  fi
done
printf '%-60s %9d MB\n\n' "${#FILES[@]} files" "$((total / 1048576))"

[ "$MODE" = "list" ] && exit 0

rclone listremotes | grep -qx "${REMOTE}:" || {
  echo "rclone remote '${REMOTE}' is not configured — see the setup notes above." >&2
  exit 1
}

for entry in "${FILES[@]}"; do
  how="${entry%%:*}"; name="${entry#*:}"
  [ -f "$SRC/$name" ] || { echo "skipping (not found): $name"; continue; }

  args=(copyto "$SRC/$name" "${REMOTE}:${BUCKET}/${name}"
        --s3-upload-cutoff 100M --s3-chunk-size 64M
        --progress --stats-one-line)
  if [ "$how" = "download" ]; then
    args+=(--header-upload "Content-Disposition: attachment; filename=\"$name\"")
    # rclone skips a file whose size and modtime already match, which on a
    # re-run would leave the header unapplied.
    args+=(--ignore-times)
  fi
  [ "$MODE" = "dry" ] && args+=(--dry-run)

  echo
  echo "-> $name"
  rclone "${args[@]}"
done

echo
echo "Done. Spot-check both kinds:"
echo "  curl -sI https://media.lovequay.com/LoveQuay-splat-transparent-640.gif"
echo "  curl -sI https://media.lovequay.com/LoveQuay-splat-transparent-3840.gif"
echo "  (only the second should carry Content-Disposition: attachment)"
