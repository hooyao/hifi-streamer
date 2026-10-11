# Working with OpenSpec

English | [简体中文](README.zh-CN.md)

OpenSpec defines behavior changes and acceptance criteria. See [Contributing](../CONTRIBUTING.md) for the end-to-end workflow.

- `specs/`: accepted capability specifications.
- `changes/`: active proposals, delta specs, designs and tracked tasks.
- `changes/archive/`: accepted changes after implementation and verification.

Use `openspec list --specs` to find existing capabilities before creating a delta. Use `openspec new change <name>`, obtain artifact instructions and validate the change before implementation. Mark tasks complete only after their tests and manual acceptance pass.

```sh
openspec validate --all --strict --no-interactive
openspec instructions apply --change <name>
```

English artifacts are canonical; Chinese editions use `.zh-CN.md`, matching structural headings and reciprocal language links. Keep their requirements and task state synchronized.

For delta specs, keep translations in `translations/zh-CN/specs/<capability>/spec.md` within the change instead of adding a second file to its parsed `specs/` tree.
