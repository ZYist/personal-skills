#!/usr/bin/env bash
# OpenAPI Spec 验证辅助脚本
# 用法: ./validate-openapi.sh <openapi-file>

set -euo pipefail

SPEC_FILE="${1:-openapi.yaml}"

if [ ! -f "$SPEC_FILE" ]; then
  echo "ERROR: File not found: $SPEC_FILE"
  exit 1
fi

ERRORS=0
WARNINGS=0

echo "=== OpenAPI Spec 验证: $SPEC_FILE ==="
echo ""

# 1. 语法检查
echo "--- [1/5] 语法检查 ---"
if python3 -c "import yaml; yaml.safe_load(open('$SPEC_FILE'))" 2>/dev/null; then
  echo "  ✅ YAML 语法合法"
elif python3 -c "import json; json.load(open('$SPEC_FILE'))" 2>/dev/null; then
  echo "  ✅ JSON 语法合法"
else
  echo "  ❌ 文件不是合法的 YAML 或 JSON"
  ERRORS=$((ERRORS + 1))
fi

# 2. OpenAPI 版本检查
echo "--- [2/5] 版本检查 ---"
VERSION=$(python3 -c "
import yaml, json, sys
try:
    data = yaml.safe_load(open('$SPEC_FILE'))
except:
    data = json.load(open('$SPEC_FILE'))
print(data.get('openapi', 'MISSING'))
" 2>/dev/null || echo "PARSE_ERROR")

if [[ "$VERSION" == 3.* ]]; then
  echo "  ✅ OpenAPI 版本: $VERSION"
else
  echo "  ❌ OpenAPI 版本异常: $VERSION (期望 3.x)"
  ERRORS=$((ERRORS + 1))
fi

# 3. 必需字段检查
echo "--- [3/5] 必需字段检查 ---"
for field in "info" "info.title" "info.version" "paths"; do
  VAL=$(python3 -c "
import yaml, json
try:
    data = yaml.safe_load(open('$SPEC_FILE'))
except:
    data = json.load(open('$SPEC_FILE'))
keys = '$field'.split('.')
obj = data
for k in keys:
    if isinstance(obj, dict):
        obj = obj.get(k)
    else:
        obj = None
        break
print('PRESENT' if obj else 'MISSING')
" 2>/dev/null || echo "ERROR")

  if [ "$VAL" = "PRESENT" ]; then
    echo "  ✅ $field 存在"
  else
    echo "  ❌ $field 缺失"
    ERRORS=$((ERRORS + 1))
  fi
done

# 4. operationId 唯一性
echo "--- [4/5] operationId 检查 ---"
OIDS=$(python3 -c "
import yaml, json
try:
    data = yaml.safe_load(open('$SPEC_FILE'))
except:
    data = json.load(open('$SPEC_FILE'))
oids = []
for path, methods in (data.get('paths') or {}).items():
    for method, op in methods.items():
        if method in ('get','post','put','patch','delete','options','head','trace'):
            oid = op.get('operationId', '')
            oids.append(oid)
missing = [i for i in oids if not i]
duplicates = [i for i in set(oids) if oids.count(i) > 1 and i]
if missing:
    print(f'MISSING:{len(missing)}')
if duplicates:
    print(f'DUPLICATE:{\",\".join(duplicates)}')
if not missing and not duplicates:
    print('OK')
" 2>/dev/null || echo "ERROR")

if [ "$OIDS" = "OK" ]; then
  echo "  ✅ 所有 operationId 唯一且非空"
else
  case "$OIDS" in
    MISSING:*) echo "  ❌ 有 ${OIDS#MISSING:} 个 operation 缺少 operationId"; ERRORS=$((ERRORS + 1)) ;;
    DUPLICATE:*) echo "  ❌ 重复的 operationId: ${OIDS#DUPLICATE:}"; ERRORS=$((ERRORS + 1)) ;;
    *) echo "  ⚠️  检查异常: $OIDS" ;;
  esac
fi

# 5. 引用检查
echo "--- [5/5] 引用完整性检查 ---"
REFS=$(python3 -c "
import yaml, json, re
try:
    data = yaml.safe_load(open('$SPEC_FILE'))
except:
    data = json.load(open('$SPEC_FILE'))

text = open('$SPEC_FILE').read()
refs = re.findall(r'\\\$ref:\s*[\"'\'']*([^\"'\'']*)[\"'\'']*', text)
# Also handle inline \$ref
refs += re.findall(r'\\$ref:\s*([^\s]+)', text)
broken = []
for ref in set(refs):
    if ref.startswith('#/'):
        parts = ref[2:].split('/')
        obj = data
        try:
            for p in parts:
                obj = obj[p]
        except (KeyError, TypeError):
            broken.append(ref)
if broken:
    print('BROKEN:' + ','.join(broken))
else:
    print('OK')
" 2>/dev/null || echo "ERROR")

if [ "$REFS" = "OK" ]; then
  echo "  ✅ 所有 \$ref 引用可解析"
elif [[ "$REFS" == BROKEN:* ]]; then
  echo "  ❌ 悬空引用: ${REFS#BROKEN:}"
  ERRORS=$((ERRORS + 1))
else
  echo "  ⚠️  检查异常: $REFS"
fi

echo ""
echo "=== 验证结果 ==="
echo "  错误: $ERRORS"
echo "  警告: $WARNINGS"
echo ""

if [ "$ERRORS" -gt 0 ]; then
  echo "❌ 验证未通过，请修复上述错误"
  exit 1
else
  echo "✅ 验证通过"
  exit 0
fi
