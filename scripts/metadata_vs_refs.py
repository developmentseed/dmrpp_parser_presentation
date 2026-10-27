"""Split DMR++ sidecars into per-chunk references vs. everything else, and
measure how much of 'everything else' is identical between two granules."""
import difflib, re, sys

def split(path):
    lines = open(path).read().splitlines()
    refs = [l for l in lines if re.search(r'<dmrpp:chunk\s[^>]*offset=', l)]
    meta = [l for l in lines if not re.search(r'<dmrpp:chunk\s[^>]*offset=', l)]
    return lines, refs, meta

def nbytes(ls): return sum(len(l) + 1 for l in ls)

a, b = sys.argv[1], sys.argv[2]
la, ra, ma = split(a); lb, rb, mb = split(b)
print(a.split('/')[-1])
print(f"  total {nbytes(la):,} B | chunk refs {len(ra):,} lines {nbytes(ra):,} B ({nbytes(ra)/nbytes(la):.0%}) | other {nbytes(ma):,} B ({nbytes(ma)/nbytes(la):.0%})")
sm = difflib.SequenceMatcher(None, ma, mb, autojunk=False)
same = sum(nbytes(ma[i:i+n]) for i, j, n in sm.get_matching_blocks())
print(f"  non-chunk bytes identical to next granule: {same:,} / {nbytes(ma):,} ({same/nbytes(ma):.1%})")
diff = [l for l in difflib.unified_diff(ma, mb, lineterm='', n=0) if l[:1] in '+-' and not l.startswith(('+++', '---'))]
print(f"  differing non-chunk lines: {len(diff)}")
for l in diff[:14]: print("   ", l.strip()[:110])
txt = open(a).read()
print("  variables:", len(re.findall(r'<(?:Float32|Float64|Int16|Int32|Int8|UInt8|UInt16|UInt32|Int64|UInt64|Byte|String) name=', txt)),
      "| attributes:", txt.count('<Attribute '),
      "| compressionType:", txt.count('compressionType='),
      "| chunkDimensionSizes:", txt.count('<dmrpp:chunkDimensionSizes>'),
      "| Dim refs:", txt.count('<Dim name='))
