---
theme: default
title: "DMR++ vs. direct parsing in VirtualiZarr"
info: |
  Why NASA virtualization should default to direct VirtualiZarr parsing rather
  than pre-generated DMR++ sidecars. Development Seed, October 2026.
layout: devseed-statement
colorSchema: light
aspectRatio: 16/9
canvasWidth: 980
fonts:
  provider: none
transition: fade
---


# Two paths, one result

## Both build the same **ManifestStore**

<div class="flow mt-6">
  <div class="flow-label">DMR++ path</div>
  <div class="flow-box flow-file">HDF5 / NetCDF4<br />granule</div>
  <div class="flow-arrow">→</div>
  <div class="flow-steps">
    <div class="flow-box flow-scan">chunk scan<small><code>build_dmrpp</code> · DAAC, ahead of time</small></div>
    <div class="flow-arrow">→</div>
    <div class="flow-box"><code>.dmrpp</code> XML<small>sidecar, stored per granule</small></div>
    <div class="flow-arrow">→</div>
    <div class="flow-box"><code>DMRPPParser</code><small>reads offsets from XML</small></div>
  </div>
  <div class="flow-arrow">→</div>
  <div class="flow-box flow-out"><code>ManifestStore</code><small>byte-range refs</small></div>

  <div class="flow-label">Direct path</div>
  <div class="flow-box flow-file">HDF5 / NetCDF4<br />granule</div>
  <div class="flow-arrow">→</div>
  <div class="flow-steps">
    <div class="flow-box flow-scan">chunk scan<small><code>HDFParser</code> · at virtualization time</small></div>
  </div>
  <div class="flow-arrow">→</div>
  <div class="flow-box flow-out"><code>ManifestStore</code><small>byte-range refs</small></div>
</div>

<div class="ds-dash mt-8">
The chunk scan is in <b>both</b> paths. DMR++ doesn't skip it, it runs it <b>earlier as part of the DAAC ingestion pipeline </b></div>

<!--
Both parsers emit the identical thing: a ManifestStore of byte-range
references into the original granule. They differ only in where those
references come from.

DMR++: the DAAC ran build_dmrpp over every granule (for Hyrax), wrote XML, and
VirtualiZarr reads offsets out of the XML.
Direct: VirtualiZarr walks each dataset's chunk B-tree itself, via h5py.
-->

---
layout: devseed
---

# Same scan, different time

## DMR++ generation and direct parsing call **the same HDF5 routine**

<div class="grid grid-cols-2 gap-5">
<div>

<p class="code-cap">BES · C++ <span>dmrpp_module/build_dmrpp_util.cc</span></p>

```cpp
if (H5Dchunk_iter(dataset, H5P_DEFAULT,
                  &chunk_cb, &chunk_udata) < 0) {
    throw BESInternalError("H5Dchunk_iter fails.", ...);
}
for (unsigned int i = 0; i < num_chunks; ++i) {
    dc->add_chunk(byte_order,
                  chunk_udata.chunk_sizes[i],
                  chunk_udata.chunk_addrs[i], ...);
}
```

</div>
<div>

<p class="code-cap">VirtualiZarr · Python <span>parsers/hdf/hdf.py</span></p>

```python
chunk_infos: list = []
dsid.chunk_iter(chunk_infos.append)  # H5Dchunk_iter

for chunk_info in chunk_infos:
    key = get_key(chunk_info)
    paths[key] = filepath
    offsets[key] = chunk_info.byte_offset
    lengths[key] = chunk_info.size
```

</div>
</div>

<div class="ds-callout mt-4">
The quoted <b>4–20 ms per file</b> parsing time for DMR++ (VirtualiZarr PR #113) is the time to read XML <i>after</i> this loop already ran on the DAAC's ingestion. Direct parsing runs it at virtualization time: <b>1–5 s</b> median per file (and there is a list of upcoming improvements).
</div>

<!--
h5py's DatasetID.chunk_iter is a thin wrapper over H5Dchunk_iter. So the
"fast" DMR++ open isn't a faster algorithm, it's a cached result.

Sources: OPENDAP/bes master, build_dmrpp_util.cc process_chunked_layout_dariable;
VirtualiZarr main (4fc1bc5), hdf.py _dataset_chunk_manifest. 1–5 s median is
from #1140 on 200 DANDI files, before the read-ahead work.
-->

---
layout: devseed
---

# The whole bill

## The scan is **a small line item**

<div class="ledger mt-4">
<div class="ledger-col">

### DMR++ path

<div class="ledger-row scan"><span>Chunk scan, every granule</span><span>paid once, by the DAAC</span></div>
<div class="ledger-row"><span>Store and serve a sidecar per granule</span><span>ongoing</span></div>
<div class="ledger-row"><span>Rebuild sidecars when BES adds fields (e.g. deflate level)</span><span>per collection</span></div>
<div class="ledger-row"><span>Find and rebuild stale or wrong sidecars</span><span>per collection</span></div>
<div class="ledger-row"><span>HDF fallback for collections without DMR++</span><span>~85% of collections</span></div>
<div class="ledger-row"><span>Keep the parser in step with format drift</span><span>VirtualiZarr + pydap</span></div>
<div class="ledger-row"><span>Maintain the generator in BES (C++)</span><span>OPeNDAP</span></div>

</div>
<div class="ledger-col">

### Direct path

<div class="ledger-row scan"><span>Chunk scan, every granule</span><span>paid once, at virtualization</span></div>
<div class="ledger-row"><span>Store the result in Icechunk</span><span>never re-scanned</span></div>
<div class="ledger-row"><span>Maintain the parser</span><span>VirtualiZarr (Python)</span></div>

<div class="ds-callout mt-5">
Once the store is written, nobody re-parses. The scan is a <b>one-time cost either way</b>
</div>

</div>
</div>

<!--
No dollar figures here on purpose. The point is the shape: the scan row is
the same on both sides, it's the only row DMR++ "saves" at open time, and it's
a one-time cost once the result is in Icechunk.

The rest of the DMR++ column is recurring, and much of it sits with DAACs and
OPeNDAP rather than with the people building virtual stores.
-->

---
layout: devseed
---

# Duplication

## Every sidecar dmr++ repeats **the same metadata**

<div class="grid grid-cols-[1.15fr_1fr] gap-8 mt-1 items-start">
<div>

<p class="code-cap">MUR SST L4 · PO.DAAC <span>one daily sidecar, 2025-06-01 vs 06-02</span></p>

<div class="dup">
  <div class="dup-bar"><div class="dup-meta" style="--w: 87%">87% repeated verbatim from the day before</div><div class="dup-refs">13%</div></div>
  <div class="dup-legend"><span class="dup-sw dup-sw-meta"></span>dtype, dims, 128 attributes, codec chains, chunk grid &amp; positions <span class="dup-sw dup-sw-refs"></span>new: offsets, lengths, dates</div>
</div>

<div class="ds-table dup-table mt-3">

| Across all 8,914 granules | Copies |
| --- | ---: |
| Attributes | **> 1 million** |
| Codec chains (shuffle + deflate) | **~60,000** |
| Sidecar XML, 115–213 KB each | **~1–2 GB** |

</div>

<div class="ds-callout mt-3">
And the copies <b>don't agree</b>: 2010 and 2018 sidecars (BES 3.20.13) have no deflate level; 2025 sidecars (BES 3.21.0) say <b>level 7</b>.
</div>

</div>
<div>

<p class="code-cap">Where it lives</p>

<div class="store">
  <div class="store-head">DMR++ · one copy per granule</div>
  <div class="store-row">
    <div class="sc"><i></i><span></span></div><div class="sc"><i></i><span></span></div><div class="sc"><i></i><span></span></div><div class="sc"><i></i><span></span></div><div class="sc"><i></i><span></span></div><div class="sc-more">× every granule</div>
  </div>
</div>

<div class="store mt-4">
  <div class="store-head">Icechunk · one copy per array</div>
  <div class="store-row">
    <div class="ic-meta"><code>zarr.json</code><small>dtype, shape, codecs, attrs: stored once</small></div>
    <div class="ic-man"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span><small>chunk manifest · offset, length per chunk</small></div>
  </div>
</div>

<div class="ds-dash mt-4">
Codec chain, dtype and attributes become <b>one array definition</b>. Only chunk refs grow with granule count.
</div>

</div>
</div>

<!--
Example: MUR-JPL-L4-GLOB-v4.1 (PO.DAAC), 8,914 granules in CMR as of
Oct 27 2026. Sidecars downloaded from the PO.DAAC archive (<granule>.nc.dmrpp).

Method: diffed the 2025-06-01 and 2025-06-02 sidecars. Granule-specific bytes
are the offset/nBytes values (26,990 B) plus metadata lines that changed
(997 B: time_coverage dates, creation date, a comment) = 27,987 of 212,578
bytes, 13.2%. Everything else is identical: 128 attributes, 8 codec chains
("shuffle deflate", deflateLevel 7), 9 variables' dtype/dims, and 1,946 of
1,947 chunkPositionInArray values.

Per-collection counts use per-sidecar ranges from 2010 / 2018 / 2025 samples:
113–128 attributes, 6–8 codec chains, 115–213 KB, times 8,914 granules.

Version drift: 2010-06-01 and 2018-06-01 sidecars carry
dmrpp:version 3.20.13-664 and no deflateLevel (the bes#954 gap);
2025-06-01 carries 3.21.0-272 with deflateLevel="7". Same collection,
same variables, different metadata depending on when build_dmrpp ran.

In Icechunk the codec chain, dtype and attributes are written once per
concatenated array; per-granule dates become the time coordinate.
-->

---
layout: devseed
---

# A second-hand copy of the file

## The sidecar can be wrong; **the file can't**

<div class="grid grid-cols-[1fr_15rem] gap-7 mt-2 items-start">
<div class="ds-table">

| Problem | Where | Fixable in VirtualiZarr? |
| --- | --- | --- |
| **Missing deflate level.** Added to `build_dmrpp` Sep 2023; older MUR SST, SWOT, ICESat sidecars lack it | OPENDAP/bes#954 | No: DAAC rebuild |
| **Wrong dtype.** 64-bit time described as `Float32`; decodes to negative timedeltas | VirtualiZarr #904 | No: DAAC rebuild |
| **Out of date.** "In some cases they are not up to date" | earthaccess #908 | No: DAAC rebuild |
| **Format drift.** New `<block/>` elements for HDF4 as an example | #85, #216 | Every BES release |

</div>
<div>

<div class="big-stat">~15%</div>
<div class="big-stat-cap">of NASA Earthdata collections have DMR++ that is <b>both downloadable and parseable</b> by VirtualiZarr (Openscapes, Aug 2025).</div>

<div class="ds-dash mt-5">So any pipeline needs the VirtualiZarr HDF parser anyway. You maintain <b>both</b>.</div>

</div>
</div>

<!--
The recurring theme: the sidecar, not the parser, is the weak link. VirtualiZarr
can only be as right as the XML it's handed, and most of these can't be fixed
in VirtualiZarr at all.

GES DISC puts OPeNDAP coverage at ~70% of its datasets; earthaccess already
falls back to HDFParser with a UserWarning when the sidecar is missing.
-->

---
layout: devseed
---

# Maintainability

## Modular parsers vs. **a C++ server module**

<div class="grid grid-cols-2 gap-7 mt-1 items-start">
<div>

<p class="code-cap">Lines of code <span>(non-test, Oct 2026)</span></p>

<div class="loc-row"><span>BES <code>dmrpp_module</code></span><div class="loc-bar" style="--w: 100%"></div><span>25,480</span></div>
<div class="loc-row"><span><code>build_dmrpp</code> (HDF5)</span><div class="loc-bar" style="--w: 11.4%"></div><span>2,916</span></div>
<div class="loc-row"><span><code>build_dmrpp_h4</code></span><div class="loc-bar" style="--w: 8.2%"></div><span>2,082</span></div>
<div class="loc-row"><span><code>HDFParser</code></span><div class="loc-bar vz" style="--w: 4.5%"></div><span>1,136</span></div>
<div class="loc-row"><span><code>NetCDF3Parser</code></span><div class="loc-bar vz" style="--w: 1.6%"></div><span>407</span></div>
<div class="loc-row"><span><code>HDF4Parser</code></span><div class="loc-bar vz" style="--w: 1%"></div><span>252</span></div>

<div class="ds-callout mt-4" style="font-size: 0.78rem">
<code>build_dmrpp</code> links BES dispatch, libdap, the NGAP container, the HDF5 handler, OpenSSL and libxml2, and ships inside a <b>460k-line</b> C/C++ server. Format changes land on BES's release cycle.
</div>

<div class="ds-dash mt-3" style="font-size: 0.78rem">
<b>HDF4 is where we need the OpenDAP team's help.</b> A more robust <code>HDF4Parser</code> needs their support: they hold the deep HDF4 knowledge (<code>hdf4_handler</code>, <code>build_dmrpp_h4</code>).
</div>

</div>
<div>

<p class="code-cap">Every VirtualiZarr parser <span>virtualizarr/parsers/typing.py</span></p>

```python
class Parser(Protocol):
    def __call__(
        self,
        url: str,
        registry: ObjectStoreRegistry,
    ) -> ManifestStore: ...
```

<div class="vz-points">

- **One small interface.** HDF5, HDF4, NetCDF3, FITS, ENVI, Zarr and Kerchunk all plug in the same way
- **Fixes land in one repo.** Fill values, var-length strings, links, chunk-grid shape: all fixed in 2026
- **Easy to contribute.** Python, `pip install`, tested on real files; Rust rewrite proposed (#1112)

</div>

</div>
</div>

<!--
Fair framing: dmrpp_module includes the Hyrax-side reader, not only the
generator. The generator alone is ~3k lines of C++ for HDF5 plus ~2k for HDF4,
but it can't be built or changed without the rest of BES.

VirtualiZarr maintainers (Max Jones, Tom Nicholas in #904) have already
favored moving DMRPPParser out of VirtualiZarr into pydap.

HDF4 ask: VirtualiZarr's HDF4Parser is 252 lines wrapping kerchunk's HDF4
decoder and handles zlib only. BES's hdf4_handler is ~62k lines of C/C++,
plus build_dmrpp_h4 (~2k), built up over years of NASA HDF4/HDF-EOS2
products. A robust HDF4Parser is where OPeNDAP's expertise matters most, so
this is a collaboration ask, not a replacement.
-->

---
layout: devseed
---

# Performance

## Direct parsing **parsing performance** is improving

<div class="ds-table mt-3">

| Change | Before | After | Status |
| --- | --- | --- | --- |
| Single B-tree walk instead of three (PR #1130), 1M-chunk file | 56,195 requests · 140 MiB | <span class="bench-after">18,736 requests · 47 MiB</span> | Merged |
| `_dataset_chunk_manifest` rewrite (PR #1137) | 2.34 s CPU · 728 MiB RSS | <span class="bench-after">0.79 s CPU · 244 MiB RSS</span> | Open |
| Read-ahead of chunk index over object storage (PR #1141), 8–12k chunks/dataset | 15–36 s | <span class="bench-after">1.9–3.1 s</span> | Open |
| Same, 137 GB file with 196,608 chunks | > 15 min | <span class="bench-after">28 s</span> | Open |
| Rust rewrite of the HDF5 parser (#1112) | | Proposed | Design |

</div>


<!--
All of this is 2026 work on the HDF parser, and the read-ahead design is
meant to carry over to the Rust rewrite.

Worth measuring together (open question): HDF vs DMR++ open time on three
representative NASA collections with #1141 applied.
-->

---
layout: devseed
---

# Recommendation

## Parse the file. **Treat DMR++ as an optional cache**

<div class="recs mt-4">
  <div class="rec">
    <h3><b>1</b>Default to direct parsing</h3>
    <p>Use <code>HDFParser</code> for HDF5/NetCDF4. It covers every granule, reads codecs and dtypes from the file, and its bugs get fixed in one repo.</p>
  </div>
  <div class="rec">
    <h3><b>2</b>Virtualize once, store in Icechunk</h3>
    <p>Pay the chunk scan one time per granule and never repeat it. That removes the only advantage a pre-built sidecar has.</p>
  </div>
  <div class="rec">
    <h3><b>3</b>DMR++ only as an opt-in cache</h3>
    <p>Only when the sidecar is newer than the granule and from a recent <code>build_dmrpp</code>. Validate a sample against <code>HDFParser</code> first.</p>
  </div>
  <div class="rec">
    <h3><b>4</b>Invest in parsers, not sidecars</h3>
    <p>Put effort into VirtualiZarr's modular parsers (incl. <code>HDF4Parser</code>), where every fix helps every collection.</p>
  </div>
</div>

<!--
Concrete follow-on: earthaccess.virtualize() defaults to DMRPPParser and warns
when it falls back to HDF. That's the reverse of this policy: it warns on the
path that is more reliable.

Open questions: has OPeNDAP regenerated the stale PO.DAAC sidecars (#908)?
Does DMRPPParser stay in VirtualiZarr or move to pydap?
-->

