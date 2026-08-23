#!/usr/bin/env bash
# Quiet daily update check for the installed kami skill.
#
# Writes a local daily cache marker, then GETs the public VERSION file on the
# default branch and compares it to the bundled VERSION. If a newer version
# exists, prints one line so the agent can relay it. It uploads no user document
# or task content; any failure is silent, so the check never blocks work.
set -u

SKILL="kami"
REPO="tw93/Kami"
DEFAULT_UPDATE_CMD="npx skills add tw93/kami/plugins/kami -a universal -g -y"
# KAMI_UPDATE_URL overrides the source (used by tests); defaults to the public VERSION.
REMOTE_URL="${KAMI_UPDATE_URL:-https://raw.githubusercontent.com/${REPO}/main/VERSION}"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
local_ver="$(tr -d '[:space:]' < "${root}/VERSION" 2>/dev/null)"
[ -n "${local_ver}" ] || exit 0

case "${root}" in
  */.claude/plugins/cache/kami/kami/*/skills/kami)
    UPDATE_CMD="claude plugin update kami"
    ;;
  */plugins/cache/kami/kami/*/skills/kami)
    UPDATE_CMD="codex plugin marketplace upgrade kami && codex plugin add kami@kami"
    ;;
  *)
    UPDATE_CMD="${DEFAULT_UPDATE_CMD}"
    ;;
esac

# Throttle: at most one check per calendar day, regardless of outcome. One
# dated marker file rewritten in place, so the cache dir does not accumulate
# a new empty update-checked-YYYY-MM-DD file every day.
day="$(date +%F 2>/dev/null)" || exit 0
if [ -n "${XDG_CACHE_HOME:-}" ]; then
  cache_root="${XDG_CACHE_HOME}"
elif [ -n "${HOME:-}" ]; then
  cache_root="${HOME}/.cache"
else
  exit 0
fi
cache_dir="${cache_root}/${SKILL}"
marker="${cache_dir}/update-checked"
[ "$(cat "${marker}" 2>/dev/null)" = "${day}" ] && exit 0
mkdir -p "${cache_dir}" 2>/dev/null || exit 0
printf '%s' "${day}" > "${marker}" 2>/dev/null || exit 0   # write first so an offline run does not retry all day
rm -f "${cache_dir}"/update-checked-2* 2>/dev/null   # sweep legacy per-day markers

command -v curl >/dev/null 2>&1 || exit 0
remote_ver="$(curl -fsSL --max-time 3 "${REMOTE_URL}" 2>/dev/null | tr -d '[:space:]')"
[ -n "${remote_ver}" ] || exit 0
[ "${remote_ver}" = "${local_ver}" ] && exit 0

# Only notify when the remote version sorts strictly higher. Numeric-field
# sort instead of `sort -V`: on a sort without -V support the old pipeline
# yielded an empty string and silently never notified again.
highest="$(printf '%s\n%s\n' "${local_ver}" "${remote_ver}" | sort -t. -k1,1n -k2,2n -k3,3n 2>/dev/null | tail -1)"
[ -n "${highest}" ] || exit 0
[ "${highest}" = "${remote_ver}" ] || exit 0

echo "Kami ${remote_ver} is available (you have ${local_ver}). Update: ${UPDATE_CMD}"
exit 0
