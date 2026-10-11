from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Plain
from astrbot.api.star import Context, Star

PLUGIN_DIR = Path(__file__).resolve().parent
DATA_DIR = PLUGIN_DIR / "data"
MENU_IMAGE = PLUGIN_DIR / "assets" / "menu.png"
LIBRARY_PATH = DATA_DIR / "default_command_library.json"

EXTRA_ENUM_LABELS = {
    "loot_table_wrapped": "战利品表（带引号）",
    "input_permission": "输入权限",
    "camera_preset": "摄像机预设",
    "recipe": "合成配方",
    "hud_element": "HUD 元素",
    "music": "音乐",
    "summonable_entity": "可召唤实体",
    "loot_tool": "战利品工具",
}


def _load_json(path: Path, expected_type: type | tuple[type, ...] = list) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, expected_type):
            return data
        logger.error(f"[我的世界查询] 数据文件结构不正确：{path.name}")
    except (OSError, json.JSONDecodeError) as exc:
        logger.error(f"[我的世界查询] 数据文件加载失败 {path.name}: {exc}")
    return [] if expected_type is list else {}


def _namespace_id(category_key: str, raw_id: str) -> str:
    if category_key in {"block", "item", "entity"} and ":" not in raw_id:
        return f"minecraft:{raw_id}"
    return raw_id


def _build_library_ids(library: dict[str, Any]) -> list[dict[str, Any]]:
    enums = library.get("enums", {})
    if not isinstance(enums, dict):
        return []

    labels_by_enum: dict[str, str] = {}
    for category in library.get("idlist", []):
        if not isinstance(category, dict):
            continue
        display_name = str(category.get("name") or "其他标识符")
        enum_names: list[str] = []
        single = category.get("list")
        plural = category.get("lists")
        if isinstance(single, str):
            enum_names.append(single)
        if isinstance(plural, list):
            enum_names.extend(str(v) for v in plural)
        for enum_name in enum_names:
            labels_by_enum.setdefault(enum_name, display_name)

    records: list[dict[str, Any]] = []
    for enum_name, entries in enums.items():
        if not isinstance(entries, dict):
            continue
        category_name = labels_by_enum.get(
            enum_name,
            EXTRA_ENUM_LABELS.get(enum_name, enum_name.replace("_", " ").capitalize()),
        )
        for raw_id, localized_name in entries.items():
            raw_id = str(raw_id)
            localized_name = str(localized_name or "").strip()
            display_name = localized_name or raw_id
            records.append({
                "name": display_name,
                "id": raw_id,
                "identifier": _namespace_id(enum_name, raw_id),
                "type": category_name,
                "category": category_name,
                "enum_group": enum_name,
                "description": "",
                "aliases": [raw_id, _namespace_id(enum_name, raw_id)],
                "source": "默认命令库",
            })
    return records


class MinecraftNetEaseQuery(Star):
    """我的世界网易版/基岩版常用指令与默认命令库 ID 查询插件。"""

    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context)
        self.config = config or {}
        self.commands = _load_json(DATA_DIR / "commands.json", list)
        library = _load_json(LIBRARY_PATH, dict)
        library_ids = _build_library_ids(library)
        if library_ids:
            self.ids = library_ids
            self.library_version = ".".join(str(x) for x in library.get("version", [])) or "未知"
            self.library_name = str(library.get("name") or "默认命令库")
            self.library_author = str(library.get("author") or "未知")
        else:
            self.ids = _load_json(DATA_DIR / "ids.json", list)
            self.library_version = "内置精简数据"
            self.library_name = "插件内置 ID 数据"
            self.library_author = "ysgl"
        logger.info(
            f"[我的世界查询] 已加载 {len(self.commands)} 条指令、{len(self.ids)} 条 ID 数据；"
            f"命令库版本：{self.library_version}。"
        )

    def _setting(self, key: str, default: Any) -> Any:
        try:
            value = self.config.get(key, default)
            return default if value is None else value
        except Exception:
            return default

    def _limit(self) -> int:
        try:
            return max(1, min(20, int(self._setting("max_results", 8))))
        except (TypeError, ValueError):
            return 8

    @staticmethod
    def _get_query(event: AstrMessageEvent, command_name: str) -> str:
        raw = str(getattr(event, "message_str", "") or "").strip()
        pattern = rf"^[\s/！!]*{re.escape(command_name)}(?:\s+|$)"
        return re.sub(pattern, "", raw, count=1, flags=re.IGNORECASE).strip()

    @staticmethod
    def _normalize(value: Any) -> str:
        return str(value or "").casefold().replace("：", ":").strip()

    def _command_score(self, record: dict[str, Any], query: str) -> int:
        q = self._normalize(query)
        if not q:
            return 0
        name = self._normalize(record.get("name", ""))
        title = self._normalize(record.get("title", ""))
        candidates = [
            name, title, self._normalize(record.get("category", "")),
            self._normalize(record.get("syntax", "")),
            self._normalize(record.get("description", "")),
            self._normalize(record.get("example", "")),
        ]
        aliases = record.get("keywords", [])
        if isinstance(aliases, list):
            candidates.extend(self._normalize(alias) for alias in aliases)
        if q == name or q == title:
            return 100
        if any(candidate and candidate.startswith(q) for candidate in candidates[:2]):
            return 80
        if any(q in candidate for candidate in candidates):
            return 50
        return 0

    def _id_score(self, record: dict[str, Any], query: str) -> int:
        q = self._normalize(query)
        if not q:
            return 0
        name = self._normalize(record.get("name", ""))
        raw_id = self._normalize(record.get("id", ""))
        identifier = self._normalize(record.get("identifier", raw_id))
        category = self._normalize(record.get("category", record.get("type", "")))
        enum_group = self._normalize(record.get("enum_group", ""))
        aliases = record.get("aliases", [])
        alias_values = [self._normalize(alias) for alias in aliases] if isinstance(aliases, list) else []
        if q in {name, raw_id, identifier} or q in alias_values:
            return 110
        if identifier.endswith(":" + q) or raw_id.endswith(":" + q):
            return 105
        if raw_id.startswith(q) or identifier.startswith(q) or name.startswith(q):
            return 85
        if q in name:
            return 70
        if q in raw_id or q in identifier:
            return 65
        if q in category or q in enum_group:
            return 15
        return 0

    def _notice(self) -> str:
        if not self._setting("show_version_notice", True):
            return ""
        return (
            "\n\n⚠️ 版本提醒：所附命令库标注版本为 " + self.library_version + "。"
            "网易版的客户端版本、游戏模式、服务器权限及附加包可能造成差异；"
            "请以目标版本实际可用的命令和 ID 为准。"
        )

    def _format_id(self, record: dict[str, Any]) -> str:
        item_type = str(record.get("type", "ID"))
        identifier = str(record.get("identifier") or record.get("id", "未知"))
        raw_id = str(record.get("id", "未知"))
        name = str(record.get("name", raw_id))
        lines = [f"🧱 [{item_type}] {name}", f"ID：{identifier}"]
        if raw_id != identifier:
            lines.append(f"命令库原始标识符：{raw_id}")
        if record.get("enum_group"):
            lines.append(f"数据类别：{record['enum_group']}")
        if item_type in ("物品", "方块"):
            lines.append(f"示例：/give @s {identifier} 1")
        elif item_type in ("实体", "可召唤实体"):
            lines.append(f"示例：/summon {identifier} ~ ~ ~")
        elif item_type == "状态效果":
            lines.append(f"示例：/effect @s {identifier} 10 1")
        elif item_type == "魔咒":
            lines.append(f"示例：/enchant @s {identifier}")
        return "\n".join(lines)

    def _format_command(self, record: dict[str, Any]) -> str:
        return (
            f"📘 [指令] /{record.get('name', '')}｜{record.get('title', '')}\n"
            f"用法：{record.get('syntax', '以游戏内提示为准')}\n"
            f"说明：{record.get('description', '')}\n"
            f"示例：{record.get('example', '/' + str(record.get('name', '')))}"
        )

    async def _send_menu(self, event: AstrMessageEvent):
        intro = (
            "🎮 我的世界网易版指令与 ID 查询\n"
            "主查询命令：/查询 <关键词>\n\n"
            "📘 查询指令：/查询 give、/查询 传送、/查询 创造\n"
            "🧱 查询 ID：/查询 钻石、/查询 命令方块、/查询 minecraft:zombie\n"
            "🔊 查询声音：/查询 声音 ambient.cave\n"
            "🧬 查询更多数据：方块、物品、实体、效果、魔咒、群系、结构、动画、粒子、声音、战利品表等\n\n"
            "兼容旧命令：/mc指令、/mcid、/mc搜索、/mc随机、/mc版本。\n"
            f"离线数据库：{self.library_name} v{self.library_version}；共加载 {len(self.ids)} 条 ID/枚举数据。\n"
            "注意：命令库中的 commands 字段为空，因此指令用法来自插件附带的常用指令表；ID/枚举查询使用你提供的默认命令库。"
        )
        if self._setting("send_menu_image", True) and MENU_IMAGE.exists():
            yield event.chain_result([Image.fromFileSystem(str(MENU_IMAGE)), Plain(intro)])
        else:
            yield event.plain_result(intro)

    @filter.command("查询")
    async def unified_query(self, event: AstrMessageEvent):
        """主查询命令：/查询 <指令、中文名称、英文 ID 或其他枚举关键词>。"""
        query = self._get_query(event, "查询")
        if not query:
            async for result in self._send_menu(event):
                yield result
            return
        mode = "all"
        if query.startswith(("指令 ", "命令 ")):
            mode, query = "command", query.split(maxsplit=1)[1].strip()
        elif query.startswith(("ID ", "id ", "标识符 ")):
            mode, query = "id", query.split(maxsplit=1)[1].strip()
        if not query:
            yield event.plain_result("请在 /查询 后输入关键词，例如：/查询 give、/查询 钻石、/查询 zombie。")
            return
        if mode != "id" and self._setting("enable_command_query", True):
            command_matches = [(self._command_score(record, query), record) for record in self.commands]
            command_matches = [(score, row) for score, row in command_matches if score > 0]
            command_matches.sort(key=lambda pair: (-pair[0], str(pair[1].get("name", ""))))
        else:
            command_matches = []
        if mode != "command" and self._setting("enable_id_query", True):
            id_matches = [(self._id_score(row, query), row) for row in self.ids]
            id_matches = [(score, row) for score, row in id_matches if score > 0]
            id_matches.sort(key=lambda pair: (-pair[0], str(pair[1].get("name", ""))))
        else:
            id_matches = []
        candidates: list[tuple[int, str, dict[str, Any]]] = []
        candidates.extend((score, "command", row) for score, row in command_matches)
        candidates.extend((score, "id", row) for score, row in id_matches)
        candidates.sort(key=lambda item: (-item[0], 0 if item[1] == "command" else 1, str(item[2].get("name", ""))))
        if not candidates:
            yield event.plain_result(
                f"没有找到「{query}」相关内容。试试：/查询 give、/查询 传送、/查询 钻石、/查询 minecraft:zombie、/查询 ambient.cave。"
                + self._notice()
            )
            return
        limit = self._limit()
        shown = candidates[:limit]
        formatted = [self._format_command(row) if kind == "command" else self._format_id(row) for _, kind, row in shown]
        title = f"🔎 查询：{query}\n命中 {len(candidates)} 条，显示前 {len(shown)} 条\n\n"
        yield event.plain_result(title + "\n\n──────────\n\n".join(formatted) + self._notice())

    @filter.command("mc菜单")
    async def mc_menu(self, event: AstrMessageEvent):
        """发送我的世界网易版指令与 ID 查询菜单图片。"""
        async for result in self._send_menu(event):
            yield result

    @filter.command("mc帮助")
    async def mc_help(self, event: AstrMessageEvent):
        """查看本插件的查询命令。"""
        async for result in self._send_menu(event):
            yield result

    @filter.command("mc指令")
    async def command_lookup(self, event: AstrMessageEvent):
        """旧命令兼容：按关键词查询常用游戏指令。"""
        if not self._setting("enable_command_query", True):
            yield event.plain_result("管理员已在插件配置中关闭指令查询功能。")
            return
        query = self._get_query(event, "mc指令")
        if not query:
            yield event.plain_result("主查询命令已改为 /查询。示例：/查询 give、/查询 传送、/查询 创造。")
            return
        matches = [(self._command_score(row, query), row) for row in self.commands]
        matches = [(score, row) for score, row in matches if score > 0]
        matches.sort(key=lambda pair: (-pair[0], str(pair[1].get("name", ""))))
        if not matches:
            yield event.plain_result(f"没有找到指令「{query}」。也可尝试 /查询 {query}。")
            return
        limit = self._limit()
        body = "\n\n──────────\n\n".join(self._format_command(row) for _, row in matches[:limit])
        yield event.plain_result(f"📘 指令查询：{query}（共 {len(matches)} 条）\n\n{body}")

    @filter.command("mcid")
    async def id_lookup(self, event: AstrMessageEvent):
        """旧命令兼容：查询物品、方块、实体以及默认命令库的其他枚举 ID。"""
        if not self._setting("enable_id_query", True):
            yield event.plain_result("管理员已在插件配置中关闭 ID 查询功能。")
            return
        query = self._get_query(event, "mcid")
        if not query:
            yield event.plain_result("主查询命令已改为 /查询。示例：/查询 钻石、/查询 zombie、/查询 ambient.cave。")
            return
        matches = [(self._id_score(row, query), row) for row in self.ids]
        matches = [(score, row) for score, row in matches if score > 0]
        matches.sort(key=lambda pair: (-pair[0], str(pair[1].get("name", ""))))
        if not matches:
            yield event.plain_result(f"没有找到 ID「{query}」。可以试试 /查询 {query}。" + self._notice())
            return
        limit = self._limit()
        body = "\n\n──────────\n\n".join(self._format_id(row) for _, row in matches[:limit])
        yield event.plain_result(f"🔎 ID 查询：{query}（共 {len(matches)} 条）\n\n{body}" + self._notice())

    @filter.command("mc搜索")
    async def combined_search(self, event: AstrMessageEvent):
        """旧命令兼容：同时搜索指令与 ID。"""
        query = self._get_query(event, "mc搜索")
        if not query:
            yield event.plain_result("主查询命令已改为 /查询。示例：/查询 钻石、/查询 give、/查询 zombie。")
            return
        command_matches = [(self._command_score(row, query), "command", row) for row in self.commands] if self._setting("enable_command_query", True) else []
        id_matches = [(self._id_score(row, query), "id", row) for row in self.ids] if self._setting("enable_id_query", True) else []
        candidates = [item for item in command_matches + id_matches if item[0] > 0]
        candidates.sort(key=lambda item: (-item[0], 0 if item[1] == "command" else 1, str(item[2].get("name", ""))))
        if not candidates:
            yield event.plain_result(f"没有找到「{query}」相关内容。请尝试 /查询 {query}。" + self._notice())
            return
        shown = candidates[: self._limit()]
        body = "\n\n──────────\n\n".join(self._format_command(row) if kind == "command" else self._format_id(row) for _, kind, row in shown)
        yield event.plain_result(f"🔎 综合搜索：{query}\n命中 {len(candidates)} 条\n\n{body}" + self._notice())

    @filter.command("mc随机")
    async def random_id(self, event: AstrMessageEvent):
        """随机查看一条内置物品、方块、实体或其他枚举 ID。"""
        if not self.ids:
            yield event.plain_result("当前 ID 数据库为空，请检查插件文件。")
            return
        row = random.choice(self.ids)
        yield event.plain_result("🎲 随机 ID\n\n" + self._format_id(row) + self._notice())

    @filter.command("mc版本")
    async def version_notice(self, event: AstrMessageEvent):
        """查看命令库版本和网易版兼容性说明。"""
        yield event.plain_result(
            "ℹ️ 数据库与版本说明\n"
            f"• 数据源：{self.library_name}，作者：{self.library_author}，版本：{self.library_version}。\n"
            f"• 当前加载 {len(self.ids)} 条 ID/枚举记录。\n"
            "• 附件中的命令库 commands 字段为空，所以指令用法来自插件自带的常用指令表。\n"
            "• 网易版功能会随客户端版本、游戏模式、服务器权限和附加包变化。\n"
            "• 部分命令需要开启作弊或操作员权限；建议以目标游戏版本内的提示为准。"
        )

    async def terminate(self):
        logger.info("[我的世界查询] 插件已卸载。")
