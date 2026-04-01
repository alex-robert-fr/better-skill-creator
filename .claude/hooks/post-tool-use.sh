#!/bin/bash
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -n "$FILE" ] && [[ "$FILE" =~ \.py$ ]]; then
  ruff check --fix "$FILE" 2>/dev/null || true
  ruff format "$FILE" 2>/dev/null || true
fi
