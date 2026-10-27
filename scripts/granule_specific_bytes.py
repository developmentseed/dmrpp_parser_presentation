"""How many bytes of a DMR++ sidecar are information unique to that granule?
Unique = the offset/nBytes values in chunk refs + non-chunk lines that differ
from the next granule. Everything else is repeated verbatim."""
import difflib, re, sys
a, b = (open(p).read().splitlines() for p in sys.argv[1:3])
is_ref = lambda l: re.search(r'<dmrpp:chunk\s[^>]*offset=', l)
refs = [l for l in a if is_ref(l)]
vals = sum(len(m) for l in refs for m in re.findall(r'(?:offset|nBytes)="(\d+)"', l))
meta_a = [l for l in a if not is_ref(l)]; meta_b = [l for l in b if not is_ref(l)]
diff = sum(len(l) for l in difflib.unified_diff(meta_a, meta_b, lineterm='', n=0)
           if l.startswith('-') and not l.startswith('---'))
total = sum(len(l) + 1 for l in a)
pos_same = sum(1 for x, y in zip([re.search(r'chunkPositionInArray="([^"]*)"', l) for l in refs],
                                 [re.search(r'chunkPositionInArray="([^"]*)"', l) for l in b if is_ref(l)])
               if x and y and x.group(1) == y.group(1))
print(f"total {total:,} B; offset+nBytes digits {vals:,} B; differing metadata {diff:,} B")
print(f"granule-specific: {vals+diff:,} B = {(vals+diff)/total:.1%}; repeated: {1-(vals+diff)/total:.1%}")
print(f"chunk refs {len(refs):,}; chunk positions identical to next granule: {pos_same:,}")
