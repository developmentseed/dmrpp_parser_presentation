# DMR++ vs. direct parsing in VirtualiZarr

A short Development Seed deck (8 slides) for a NASA technical group that is
deciding how to virtualize Earthdata collections going forward. It argues for
**direct VirtualiZarr parsing** over relying on pre-generated DMR++ sidecars:

- DMR++ opens faster only because the chunk scan already ran: `build_dmrpp`
  and `HDFParser` both walk the chunk index with `H5Dchunk_iter`.
- That scan is a small, one-time cost next to generating, storing, rebuilding
  and fixing a sidecar for every granule.
- Sidecars repeat the same metadata for every granule and can be stale or
  wrong, the file itself can't be.
- VirtualiZarr's parsers are small, modular Python behind one interface, while
  DMR++ generation lives in a C++ data server (BES). HDF4 is the exception:
  a more robust `HDF4Parser` needs OPeNDAP's help.

The source material is the "DMR++ vs. native HDF parsing in VirtualiZarr"
review doc.

## Slides

1. **Two paths, one result.** Both paths produce the same `ManifestStore`, and both include the chunk scan
2. **Same scan, different time.** The `build_dmrpp` and `HDFParser` code side by side
3. **The whole bill.** The scan as one small item in each path's costs
4. **Duplication.** MUR SST sidecars: 87% repeated day to day, and copies disagree across BES versions
5. **A second-hand copy of the file.** Documented sidecar problems and ~15% coverage
6. **Maintainability.** Lines of code, the `Parser` protocol, and the HDF4 ask to OPeNDAP
7. **Performance.** 2026 HDF parser benchmarks
8. **Recommendation.** Direct parsing by default, DMR++ as an opt-in cache

## Running locally

Requires Node 18+.

```sh
npm install
npm run dev        # http://localhost:3030 (live-reloads as you edit slides.md)
```

- Presenter view with speaker notes: http://localhost:3030/presenter/
- Overview of all slides: http://localhost:3030/overview/

## Exporting

```sh
npx slidev export slides.md --output slides.pdf
npx slidev export slides.md --format png --output png   # one PNG per slide
```

Exporting uses `playwright-chromium`, which is already a dev dependency.
`slides.pdf` in this folder is a recent export.

## Editing

- Slides are separated by `---`. Every slide uses one of two DevSeed layouts
  in `layouts/`: `devseed` (label, heading, body) or `devseed-statement` (one
  big line). In each slide, `# H1` is the small uppercase label and `## H2` is
  the heading. Wrap key phrases in `**bold**` to show them in DevSeed blue.
- The first slide takes its layout from the headmatter at the top of
  `slides.md` (`layout: devseed-statement`).
- `<!-- ... -->` at the end of a slide becomes its speaker notes. The notes
  hold the numbers, methods and sources behind each slide.
- `styles/devseed.css` is the DevSeed theme, copied from the CNG Forum 2026
  deck. `styles/index.css` holds this deck's own components (flow diagram,
  cost ledger, duplication bars, lines-of-code bars, recommendation cards).
- `setup/shiki.ts` forces a dark code theme because code sits on navy panels.
- `package.json` pins `fuse.js` to 7.1.0 through `overrides`. Newer versions
  make Slidev's "go to slide" menu show all the time.

## Where the numbers come from

All measurements were taken in Oct 2026.

- **Code excerpts and line counts:** shallow clones of
  [OPENDAP/bes](https://github.com/OPENDAP/bes) and
  [zarr-developers/VirtualiZarr](https://github.com/zarr-developers/VirtualiZarr)
  (`main`, 4fc1bc5). Non-test `.cc`/`.h` and `.py` files, counted with `wc -l`.
- **Duplication slide:** MUR SST L4 (`MUR-JPL-L4-GLOB-v4.1`, PO.DAAC). The
  granule count (8,914) is from CMR. Sidecars are `<granule>.nc.dmrpp` from the
  PO.DAAC archive, which needs Earthdata Login credentials in `~/.netrc`.
  Compared granules: 2025-06-01 vs 2025-06-02, plus 2010-06-01 and 2018-06-01
  to check the BES version and `deflateLevel`.
- **Problems, coverage and benchmarks:** the GitHub issues and PRs cited in
  each slide's speaker notes.

To re-run the duplication measurements on any two consecutive sidecars:

```sh
python3 scripts/metadata_vs_refs.py day1.dmrpp day2.dmrpp        # chunk refs vs. other metadata, and how much matches
python3 scripts/granule_specific_bytes.py day1.dmrpp day2.dmrpp  # bytes unique to the granule vs. repeated
```

## Layout

```
slides.md     the deck
slides.pdf    latest PDF export
layouts/      DevSeed Slidev layouts
styles/       DevSeed theme + deck-specific styles
setup/        Slidev setup (code highlighting theme)
public/       DevSeed logo
scripts/      DMR++ duplication measurement scripts
```
