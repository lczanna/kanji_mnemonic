#!/usr/bin/env python3
"""
Check and repair the coloured strokes of the look-alike mnemonics (data/lookalike_groups.json "mn").

KanjiVG groups strokes by component (<g kvg:element="反">), so when a feature names a component (反, 古, 欠, 扌…)
its strokes are taken from there instead of from the hand-picked numbers. Problems are listed:
  - a label that names a feature but has no strokes (unless it's an absence: "no …", "nothing …"),
  - strokes covering most of the kanji (that colours everything and points at nothing).

  python3 tools/fix_lookalike_strokes.py kanjivg.xml.gz
"""
import gzip, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RADICAL_FORMS = {'扌': '手', '忄': '心', '氵': '水', '亻': '人', '彳': '彳', '辶': '辶', '阝': '阝', '宀': '宀', '艹': '艸', '⺮': '竹', '尸': '尸', '土': '土', '口': '口'}


def element_strokes(xml):
    """kanji -> {component: [stroke indexes]} from KanjiVG's element groups."""
    out = {}
    for m in re.finditer(r'<kanji id="kvg:kanji_([0-9a-f]{5})">(.*?)</kanji>', xml, re.S):
        ch, body = chr(int(m.group(1), 16)), m.group(2)
        comps, stack, n = {}, [], 0
        for t in re.finditer(r'<g\b([^>]*)>|</g>|<path [^>]*?-s(\d+)"', body):
            if t.group(0).startswith('</g'):
                stack and stack.pop()
            elif t.group(0).startswith('<g'):
                e = re.search(r'kvg:element="([^"]+)"', t.group(1))
                stack.append(e.group(1) if e else None)
            else:
                i = int(t.group(2)) - 1
                for e in stack:
                    if e:
                        comps.setdefault(e, []).append(i)
        for e in comps:
            comps[e] = sorted(set(comps[e]))
        out[ch] = comps
    return out


def main():
    xml = gzip.open(sys.argv[1]).read().decode()
    comps = element_strokes(xml)
    groups = json.loads((ROOT / 'data' / 'lookalike_groups.json').read_text(encoding='utf8'))
    issues, fixed = [], 0
    for g in groups:
        for k, m in (g.get('mn') or {}).items():
            total = sum(1 for e in comps.get(k, {}).get(k, [])) or None
            text = m.get('label', '') + ' ' + m.get('feature', '')
            named = [c for c in re.findall(r'[一-鿿⺀-⻳々]', text) if c != k]
            found = None
            for c in named:   # the component the feature names, as KanjiVG groups it in this kanji
                for cand in (c, RADICAL_FORMS.get(c)):
                    if cand and cand in comps.get(k, {}) and cand != k:
                        found = comps[k][cand]; break
                if found:
                    break
            absence = re.match(r'\s*(no|nothing|without|bare|plain)\b', m.get('label', ''), re.I)
            if found and found != m.get('strokes'):
                m['strokes'] = found; fixed += 1
            if not m.get('strokes') and not absence:
                issues.append(f"{g['id']} {k}: '{m.get('label')}' has no strokes")
            if total and len(m.get('strokes', [])) * 10 > total * 7:
                issues.append(f"{g['id']} {k}: '{m.get('label')}' colours {len(m['strokes'])} of {total} strokes")
    (ROOT / 'data' / 'lookalike_groups.json').write_text(json.dumps(groups, ensure_ascii=False, indent=1), encoding='utf8')
    print(f'{fixed} taken from KanjiVG components; {len(issues)} to look at:')
    print('\n'.join(issues))


if __name__ == '__main__':
    main()
