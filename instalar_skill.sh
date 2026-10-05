#!/usr/bin/env bash
# Instala la skill en Antigravity (global) y, si existe, en Claude Code. Uso: bash instalar_skill.sh
set -e
ORIGEN="$(cd "$(dirname "$0")" && pwd)/skills/clips-automaticos"
DESTINOS=("$HOME/.gemini/config/skills/clips-automaticos")
[ -d "$HOME/.claude" ] && DESTINOS+=("$HOME/.claude/skills/clips-automaticos")
for d in "${DESTINOS[@]}"; do
  mkdir -p "$(dirname "$d")"; rm -rf "$d"; cp -r "$ORIGEN" "$d"; echo "Skill instalada en $d"
done
echo "Reinicia Antigravity y pídele: 'monta los clips automáticos' (o escribe /clips-automaticos)."
