# 使用OpenSpec

[English](README.md) | 简体中文

OpenSpec定义行为变更和验收标准，完整流程见[贡献指南](../CONTRIBUTING.zh-CN.md)。

- `specs/`：已接受的能力规格。
- `changes/`：进行中的proposal、delta规格、design及任务。
- `changes/archive/`：实现与验证完成后接受的变更。

创建delta前用 `openspec list --specs` 查找已有能力。用 `openspec new change <name>` 创建变更，获取artifact指引，实现前校验。只有测试及手动验收通过后才完成任务。

```sh
openspec validate --all --strict --no-interactive
openspec instructions apply --change <name>
```

英文artifact为主文件，中文使用 `.zh-CN.md`，结构标题保持一致并添加双向语言链接。同步更新需求与任务状态。

Delta规格翻译放在change内的 `translations/zh-CN/specs/<capability>/spec.md`，不要在CLI读取的 `specs/` 目录添加第二个文件。
