# Working with OpenSpec

OpenSpec defines behavior changes and acceptance criteria. See [Contributing](../CONTRIBUTING.md) for the end-to-end workflow.

- `specs/`: accepted capability specifications.
- `changes/`: active proposals, delta specs, designs and tracked tasks.
- `changes/archive/`: accepted changes after implementation and verification.

Use `openspec list --specs` to find existing capabilities before creating a delta. Use `openspec new change <name>`, obtain artifact instructions and validate the change before implementation. Mark tasks complete only after their tests and manual acceptance pass.

```sh
openspec validate --all --strict --no-interactive
openspec instructions apply --change <name>
```

All content under `openspec/` must be English only, including guides, proposals, designs, tasks, specifications and configuration. Do not add translated editions or language-switch links. Product and contributor documentation outside this directory remains bilingual.
