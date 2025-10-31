#!/usr/bin/env python3
"""Fix indentation in app.py"""
with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Fix line 73 - else should have 16 spaces (same as if)
if len(lines) > 72:
    line73 = lines[72]
    # Check current indentation
    stripped = line73.lstrip()
    if stripped.startswith('else:'):
        # Should have 16 spaces (same as if success: on line 71)
        lines[72] = '                else:\n'
        print(f"Fixed line 73: {repr(lines[72])}")

# Fix line 91 - est should have 4 spaces (function body)
if len(lines) > 90:
    line91 = lines[90]
    if 'est = timezone' in line91 and not line91.startswith('    est'):
        lines[90] = '    est = timezone(timedelta(hours=-5))\n'
        print(f"Fixed line 91: {repr(lines[90])}")

# Fix line 92
if len(lines) > 91:
    line92 = lines[91]
    if 'edt = timezone' in line92 and not line92.startswith('    edt'):
        lines[91] = '    edt = timezone(timedelta(hours=-4))\n'
        print(f"Fixed line 92: {repr(lines[91])}")

# Fix line 93
if len(lines) > 92:
    line93 = lines[92]
    if 'now_utc = datetime' in line93 and not line93.startswith('    now_utc'):
        lines[92] = '    now_utc = datetime.now(timezone.utc)\n'
        print(f"Fixed line 93: {repr(lines[92])}")

# Fix line 94
if len(lines) > 93:
    line94 = lines[93]
    if 'is_dst = now_utc.month' in line94 and not line94.startswith('    is_dst'):
        lines[93] = '    is_dst = now_utc.month >= 3 and now_utc.month < 11\n'
        print(f"Fixed line 94: {repr(lines[93])}")

# Fix line 213
if len(lines) > 212:
    line213 = lines[212]
    if 'else:' in line213:
        # Should have 8 spaces (same as if on line 210)
        lines[212] = '        else:\n'
        print(f"Fixed line 213: {repr(lines[212])}")

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
    
print("Done fixing indentation")

