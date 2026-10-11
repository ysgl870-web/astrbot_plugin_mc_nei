# 我的世界网易版指令与 ID 查询（AstrBot 插件）

**作者：ysgl｜版本：1.1.0**

一个适配 AstrBot 的离线检索插件。主命令改为 `/查询`，既可以查常用游戏指令，也可以检索你提供的“默认命令库”中的方块、物品、实体和各类枚举标识符。

## 快速使用

| 命令 | 用法 | 作用 |
|---|---|---|
| `/查询` | `/查询` | 显示菜单图片和查询帮助 |
| `/查询` | `/查询 give` | 搜索常用游戏指令用法 |
| `/查询` | `/查询 传送` | 按中文关键词搜索指令 |
| `/查询` | `/查询 钻石` | 查询物品、方块或其他匹配 ID |
| `/查询` | `/查询 minecraft:zombie` | 按英文 ID 查询 |
| `/查询` | `/查询 ambient.cave` | 查询声音等枚举数据 |
| `/查询` | `/查询 指令 give` | 只在指令数据中搜索 |
| `/查询` | `/查询 ID 钻石` | 只在 ID/枚举数据中搜索 |
| `/mc随机` | `/mc随机` | 随机查看一条 ID/枚举记录 |
| `/mc版本` | `/mc版本` | 查看数据来源与版本提醒 |
| `/mc菜单`、`/mc帮助` | `/mc菜单` | 兼容旧菜单命令 |

旧版 `/mc指令`、`/mcid` 和 `/mc搜索` 也保留兼容，但日常使用推荐统一输入 `/查询 <关键词>`。

## 接入的命令库

已将随消息上传的 `默认命令库(1).json` 完整放入 `data/default_command_library.json`，插件会读取 `idlist` 与 `enums` 并自动展开数据。目前共覆盖该文件中 25 个枚举表，包含方块、物品、实体、状态效果、魔咒、迷雾、生物群系、结构、伤害来源、实体事件、实体族、动画、动画控制器、粒子发射器、声音、战利品表、配方、音乐等类别。

查询展示保留原始标识符，并为方块、物品、实体附带便于复制的 `minecraft:` 命名空间形式。带引号、带命名空间或带路径的标识符尽量保持命令库原样显示。

**数据说明：** 上传的 JSON 中 `commands` 字段是空对象 `{}`，没有内置可用的指令用法记录。因此，本插件继续使用原插件 `data/commands.json` 中整理的常用指令用法；ID/枚举查询则完整适配上传的命令库。这样不会把不存在的指令数据伪装成来自命令库。

## 安装

1. 解压 ZIP，将其中的 `astrbot_plugin_mc_nei` 文件夹放进 `AstrBot/data/plugins/`。
2. 确认文件夹下包含 `main.py`、`metadata.yaml`、`_conf_schema.json`、`data/` 与 `assets/`。
3. 在 AstrBot WebUI 的插件页面启用或重载插件。
4. 发送 `/查询` 显示菜单，再发送 `/查询 钻石` 或 `/查询 give` 测试。

插件只做本地数据查询，不会向游戏服务器执行游戏命令，也不需要 API Key 或额外网络服务。

## 版本兼容

上传的命令库标注版本为 `1.21.0.21`（按文件的 version 数组格式拼接）。网易版实际可用的指令和 ID 可能受到客户端版本、服务器权限、教育/开发模式和附加包影响，使用结果时请以目标版本实测为准。

## 数据来源与鸣谢

- 命令库数据：用户提供的“默认命令库”，元数据署名 **CA制作组**。本插件保留原始 JSON 数据与标识符。
- AstrBot 插件开发指南：https://docs.astrbot.app/dev/star/plugin-new.html
- QQ 官方机器人开发文档：https://bot.q.qq.com/wiki/develop/api-v2/
- Microsoft Learn，Popular Commands：https://learn.microsoft.com/en-us/minecraft/creator/documents/commandspopularcommands?view=minecraft-bedrock-stable
