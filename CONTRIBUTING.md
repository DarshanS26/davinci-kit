# Contributing

Thanks for helping improve DaVinci Resolve Kit.

## Useful contributions

- Distro-specific dependency notes
- Bug reports with `davinci-kit-info` output
- Tested codec compatibility results
- Safer launch fixes for different GPU/desktop combinations
- GUI polish, screenshots, and packaging work

## Bug reports

Please include:

- Linux distro and version
- DaVinci Resolve version and Free/Studio edition
- GPU model and driver
- Desktop session: X11 or Wayland
- Output from `davinci-kit-info`
- Exact command you ran and the error output

Do not upload private media unless you are comfortable making it public. A short `ffprobe` output is usually enough.

## Development checks

Before opening a PR, run:

```bash
bash -n install.sh
for f in bin/* lib/*.sh; do bash -n "$f"; done
python3 -m py_compile $(find gui -name '*.py')
```

If you change transcoding or export behavior, test with `-n` dry-run first and include the generated ffmpeg command in the PR notes.

## Style

Keep changes small and boring. Prefer shell/Python standard libraries and existing dependencies. Avoid new packaging formats or heavy abstractions unless they solve a real user problem.
