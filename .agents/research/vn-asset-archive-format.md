# VN Asset Archive Format: `7z` vs `tar.zst`

## Decision

Use `.7z` as the default archive format for optimized visual novel game folders when the target workflow includes Android/MiXplorer. Use 7-Zip LZMA2 at level `7`:

```sh
7z a -t7z -mx=7 -m0=LZMA2 -mmt=on -ms=on game.7z game/
7z x game.7z
```

Keep `.tar.zst` as an opt-in format when the archive will mainly be unpacked on Linux or by tools that handle `.tar.zst` as a single archive. Do not use Zstd `--ultra` levels (`20+`) or `--long` mode for the default tar.zst path. If archive creation speed becomes a real workflow problem, use zstd level `15` as the faster high-compression tar.zst preset.

## Rationale

`7z` is the better default for this phone-centered workflow because it is a single archive format in MiXplorer. `.tar.zst` can be treated as two layers, first Zstandard then tar, which makes extraction feel like a two-step operation on Android even though it is technically a good archival format.

`tar.zst` is still excellent when extraction latency and memory matter on systems with first-class support. Zstd's own CLI manual describes the decoder as faster than 500 MB/s per core and "roughly stable at all compression settings"; the same manual says normal levels are `1-19`, default `3`, and `--ultra` levels `20+` use much more memory, including more decompression memory. That makes level `19` the highest normal Zstd level before the documented ultra-memory tradeoff. The manual also warns that `--long` increases compressor and decompressor memory, so avoid it for Android-ish targets. Sources: [Zstd CLI manual](https://raw.githubusercontent.com/facebook/zstd/dev/programs/zstd.1.md), [Zstd API manual](https://facebook.github.io/zstd/doc/api_manual_v1.5.7.html).

GNU tar supports `--zstd`, recognizes `.zst` / `.tzst` suffixes for auto-compression, and can use `-I` / `--use-compress-program` when explicit compressor options such as `zstd -19` are needed. Compressed tar archives are stream archives and cannot be updated in place, but the VN workflow here is whole-folder pack/unpack, where that is acceptable. Source: [GNU tar compression manual](https://www.gnu.org/software/tar/manual/html_section/Compression.html).

`7z` has a larger extraction penalty than zstd, but it is credible for maximum ratio and works better as a single Android-managed archive. 7-Zip documents `7z` as a high-ratio format with solid compression and LZMA/LZMA2 as the default/general methods. Its LZMA SDK lists decompression at 30-100 MB/s on modern 4 GHz Intel/AMD/ARM CPUs, 5-15 MB/s on simple 1 GHz RISC CPUs, and decompression memory as `8-32 KB + DictionarySize`. In current 7-Zip defaults, `-mx7` uses a 128 MB dictionary on 64-bit builds and `-mx9` uses 256 MB; 32-bit builds cap those defaults at 64 MB. Sources: [7z format](https://www.7-zip.org/7z.html), [LZMA SDK](https://www.7-zip.org/sdk.html), [7-Zip 24.09 release notes](https://github.com/ip7z/7zip/releases/tag/24.09).

For VN folders, ratio is workload-dependent. Optimized games often contain already-compressed media plus many small scripts/assets, so neither format should be assumed to win universally. 7-Zip's FAQ notes that dictionary size and sorting by type can make a large ratio difference for similar files, but also documents drawbacks from non-default ordering. That supports treating `.7z` as a benchmarked "smallest output" option, not the default for local desktop/Android-ish extraction. Source: [7-Zip FAQ](https://www.7-zip.org/faq.html).

## Default

- Default format: `.7z`
- Default compression level: `7z -mx=7 -m0=LZMA2 -ms=on`
- Default command: `7z a -t7z -mx=7 -m0=LZMA2 -mmt=on -ms=on game.7z game/`
- Avoid by default: `7z -mx9`, `zstd --ultra`, and `zstd --long`
- Optional fastest-unpack mode: `.tar.zst` with `zstd -19 -T0`

## Source Notes

- Zstandard reference implementation and CLI: <https://github.com/facebook/zstd>
- Zstd CLI manual: <https://raw.githubusercontent.com/facebook/zstd/dev/programs/zstd.1.md>
- Zstd API manual: <https://facebook.github.io/zstd/doc/api_manual_v1.5.7.html>
- GNU tar compression docs: <https://www.gnu.org/software/tar/manual/html_section/Compression.html>
- 7-Zip `7z` format docs: <https://www.7-zip.org/7z.html>
- 7-Zip LZMA SDK docs: <https://www.7-zip.org/sdk.html>
- 7-Zip 24.09 dictionary-size release note: <https://github.com/ip7z/7zip/releases/tag/24.09>
- 7-Zip FAQ on solid archive sorting/dictionary tradeoffs: <https://www.7-zip.org/faq.html>
