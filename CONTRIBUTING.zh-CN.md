# 贡献指南

[English](CONTRIBUTING.md) | 简体中文

## 修改代码前

阅读[架构](docs/design/AUDIO-ARCHITECTURE.zh-CN.md)、[音源契约](docs/design/SOURCE-MODULES.zh-CN.md)及相关 OpenSpec 需求。可选音源停用、断线或更新时，DLNA 仍应可用。

使用范围明确的分支并提交 pull request。受保护的 `main` 要求 PR、必要检查通过及 review 讨论已解决；禁止直接推送、强推和删除，管理员也不能绕过。生成的测试报告放在被忽略的输出目录或 CI artifacts 中。不要提交凭据、本地设备清单、聊天记录、安装日记或原始日志。

## OpenSpec 工作流

未安装 OpenSpec CLI 时：

```sh
npm install -g @fission-ai/openspec@1.14.1
openspec list
openspec list --specs
```

为可观察的行为变更创建具名 change：

```sh
openspec new change <change-name>
openspec status --change <change-name>
openspec instructions proposal --change <change-name>
```

按依赖顺序填写：

1. `proposal.md`：问题、范围、能力与影响。
2. `specs/<capability>/spec.md`：行为需求和可测试场景。
3. `design.md`：需要时记录实现选择、依赖与取舍。
4. `tasks.md`：有明确完成标准的实现与验证任务。

使用 `openspec instructions <artifact> --change <change-name>` 获取 schema 指引。新需求使用 `SHALL` 或 `MUST`，场景使用 `#### Scenario:`。修改 delta 时保留完整的已有需求块。

```sh
openspec validate <change-name> --strict --no-interactive
openspec instructions apply --change <change-name>
```

实现任务、增加有意义的测试、更新受影响文档。只有完整验收条件通过才能勾选任务。硬件手动检查没有结果时保持未完成；mock 测试不能替代硬件验收。

## 文档与注释

- 代码注释和 docstring 使用英文。
- `openspec/` 以外的文档，英文使用默认文件名，中文使用 `.zh-CN.md`，顶部包含双向语言切换链接。
- 两版同时更新，包括示例与支持范围。
- `openspec/` 内的指南、提案、设计、任务、规格及配置全部只能用英文；禁止中文版、翻译目录及语言切换链接。
- `AGENTS.md` 是模块职责、源码入口和贡献指引的简明入口，详细操作说明放在正式文档。
- 记录可复现的行为与支持边界，不记录聊天事件。

## 验证

```sh
python3 -m unittest discover -s tests -v
openspec validate --all --strict --no-interactive
git diff --check
```

修改输出控制、容器或部署时，运行[测试指南](docs/testing/README.zh-CN.md)中相关硬件测试。修改镜像时运行体积与版本检查。提交 PR 前检查文档语言链接。

## Pull request 与 review

说明具体问题、最终行为、测试和剩余限制。引用 OpenSpec change，列出仍需要的手动验收，不声称超出已有证据的硬件支持。

实现与验收 review 完成后：

```sh
openspec archive <change-name>
openspec validate --all --strict --no-interactive
```

归档更新主规格，不能代替实现或验证。

## 许可

项目尚未声明许可证。引入第三方代码或分发服务二进制前，应核对上游条款。
