#!/usr/bin/env bash
# Instala la skill en Antigravity, Codex y (si existe) Claude Code. Uso: bash instalar_skill.sh
set -e
ORIGEN="$(cd "$(dirname "$0")" && pwd)/skills/clips-automaticos"
DESTINOS=("$HOME/.gemini/config/skills/clips-automaticos" "$HOME/.agents/skills/clips-automaticos")
[ -d "$HOME/.claude" ] && DESTINOS+=("$HOME/.claude/skills/clips-automaticos")
for d in "${DESTINOS[@]}"; do
  mkdir -p "$(dirname "$d")"; rm -rf "$d"; cp -r "$ORIGEN" "$d"; echo "Skill instalada en $d"
done
echo "Listo: Antigravity (reinícialo), Codex y Claude Code. Pídele al agente: 'monta los clips automáticos'."
