# Development

[← Docs home](README.md)

## Layout

```
hyperject-main/
├── pyproject.toml            packaging + entry point + pytest config
├── Makefile                  install / test / loop / clean
├── config.example.json       reference config
├── docs/                     this wiki
├── examples/                 filled-in example configs
├── tests/                    pytest suite (unit + contract)
└── src/hyperject/
    ├── cli.py  core.py  ui.py  transcript.py
    ├── base.py  mwbase.py  registry.py
    ├── collector.py  detector.py
    ├── modules/              one file per target
    └── middleware/           one file per hook
```

## Make targets

```bash
make dev      # editable install (source edits take effect immediately)
make install  # pipx install the CLI
make test     # run the pytest suite
make loop     # full mock -> run -> detect loop in ./.demo
make lint     # byte-compile all sources
make clean    # remove build artifacts and the demo dir
```

## Tests

```bash
make test         # or: python3 -m pytest -q
```

The suite covers the engine (classification, retries, dry-run), config
validation, the transcript exporters, the detector, the CLI, key handling, and
UI/color. Two of the files are **contract tests** that parametrize over every
discovered plugin:

- `test_modules_contract.py` — every target module must expose a valid
  `default_config()` and `plan()` (correct `Prepared` shape, `bulk` honors
  `run.count`, techniques within `supported_techniques`).
- `test_middleware.py` — every middleware must be a valid `Middleware` subclass
  and be instantiable with no options.

So a newly added `modules/` or `middleware/` file is checked automatically — run
`make test` after adding one.

`test_no_emoji.py` scans the package (source, docs, config) and fails if any
emoji / pictograph is introduced. Plain typography (arrows, box-drawing, dashes)
is allowed; emoji are not — the project stays emoji-free.

## Build-artifact gotcha

`pipx install .` (and `make install`) regenerate `build/` and `*.egg-info/` in the
source tree. If a source edit doesn't seem to take effect, those can shadow it:

```bash
make clean
pipx install . --force --pip-args=--no-cache-dir
```

`make clean` removes them; they're gitignored.

## Releasing

Version lives in three places — bump them together:

- `src/hyperject/__init__.py` (`__version__`)
- `pyproject.toml` (`version`)
- `src/hyperject/transcript.py` (HAR `creator.version`)

Then `make clean && make test && make install`.

## Safety invariants (do not remove)

- No built-in target hostnames or credentials — everything comes from config.
- The placeholder guard blocks runs against unfilled configs.
- `--dry-run` sends nothing.
- The `allowlist` middleware can hard-block any off-list host.
- The project stays emoji-free (`test_no_emoji.py` enforces it).

See [Concepts → Safety model](concepts.md#safety-model).
