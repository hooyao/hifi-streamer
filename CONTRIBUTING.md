# Contributing

English | [简体中文](CONTRIBUTING.zh-CN.md)

## Before changing code

Read the [architecture](docs/design/AUDIO-ARCHITECTURE.md), [source contract](docs/design/SOURCE-MODULES.md) and relevant OpenSpec requirements. Keep DLNA available when an optional source is disabled, disconnected or updated.

Use a focused branch and submit a pull request. The protected `main` branch requires a PR, passing required checks and resolved review conversations; direct pushes, force pushes and deletion are disabled, including administrator bypass. Generated test reports belong in an ignored output directory or CI artifacts. Do not commit credentials, local device inventories, conversation transcripts, installation diaries or raw logs.

## OpenSpec workflow

Install the OpenSpec CLI if it is unavailable:

```sh
npm install -g @fission-ai/openspec@1.14.1
openspec list
openspec list --specs
```

Create a named change for an observable behavior change:

```sh
openspec new change <change-name>
openspec status --change <change-name>
openspec instructions proposal --change <change-name>
```

Fill the artifacts in dependency order:

1. `proposal.md`: problem, scope, capabilities and impact.
2. `specs/<capability>/spec.md`: behavior requirements and testable scenarios.
3. `design.md`: implementation choices, dependencies and trade-offs when needed.
4. `tasks.md`: implementation and validation tasks with explicit completion criteria.

Use `openspec instructions <artifact> --change <change-name>` to obtain the schema-specific guidance. New requirements use `SHALL` or `MUST` and `#### Scenario:` headings. Preserve existing requirement blocks when writing a modified delta.

```sh
openspec validate <change-name> --strict --no-interactive
openspec instructions apply --change <change-name>
```

Implement the tasks, add meaningful tests and update affected documentation. Mark a task complete only when its full acceptance criterion passes. Keep manual hardware checks incomplete until results are available; a passing mocked test does not replace hardware validation.

## Documentation and comments

- Code comments and docstrings are English.
- English Markdown uses the default filename; the Chinese edition uses `.zh-CN.md`.
- OpenSpec delta specs are the exception: keep only canonical `spec.md` under `specs/`, and place its Chinese edition under `translations/zh-CN/specs/` in the change directory so CLI validation can distinguish translations from deltas.
- Every maintained document starts with reciprocal language links.
- Update both editions together, including examples and capability boundaries.
- OpenSpec structural headings and `SHALL/MUST` remain English in both editions.
- `AGENTS.md` is the concise entry point to module ownership, source files and contributor guidance. Detailed operational instructions belong in documentation.
- Document reproducible behavior and support boundaries, not chat events.

## Validation

```sh
python3 -m unittest discover -s tests -v
openspec validate --all --strict --no-interactive
git diff --check
```

Run relevant hardware tests from the [test guide](docs/testing/README.md) when changing output control, containers or deployment. Run image-size/version checks for changed images. Check reciprocal document links before opening a pull request.

## Pull requests and review

Describe the concrete problem, resulting behavior, tests and remaining limitations. Reference the OpenSpec change, list any manual acceptance still required and avoid claiming broader hardware support than the evidence establishes.

After implementation and acceptance are reviewed:

```sh
openspec archive <change-name>
openspec validate --all --strict --no-interactive
```

Archiving updates the main specs; it is not a substitute for implementation or verification.

## Licensing

The project does not yet declare a license. Do not add third-party code or redistribute a service binary without checking its upstream terms.
