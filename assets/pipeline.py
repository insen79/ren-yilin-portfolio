#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AI 内容流水线：选题 → 脚本 → 质检 → 落盘。

用法：
    python pipeline.py --mock        # 不调用 API，跑通流程（免费）
    python pipeline.py               # 调用 DeepSeek，需要环境变量 DEEPSEEK_API_KEY

纯标准库实现，不需要 pip install。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
OUT = ROOT / "output"
PROMPTS = ROOT / "prompts"
API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
THRESHOLD = 7.0


# ────────────────────────── 模型调用 ──────────────────────────

def call_llm(system: str, user: str, retries: int = 2) -> dict:
    """调 DeepSeek 的 JSON 模式，返回解析后的 dict。"""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise RuntimeError("没有 DEEPSEEK_API_KEY，请先设置环境变量，或用 --mock 运行")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.8,
        "max_tokens": 2000,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    for attempt in range(retries + 1):
        req = urllib.request.Request(
            API_URL,
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"]
            return json.loads(text)
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            if attempt >= retries:
                raise RuntimeError(f"调用失败：{exc}") from exc
            time.sleep(2 * (attempt + 1))
    return {}


def load_prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


# ────────────────────────── 三步生成 ──────────────────────────

def expand_topic(topic: str, mock: bool) -> dict:
    if mock:
        return {
            "audience": "22-28 岁、正在找工作或想转行的人",
            "pain": "投了很多简历没回音，不知道自己哪里不行",
            "angle": f"「{topic}」这件事，大多数人第一步就做反了",
        }
    return call_llm(load_prompt("01_topic.md"), f"选题：{topic}")


def make_script(topic: str, brief: dict, mock: bool) -> dict:
    if mock:
        return {
            "hook": "投了 80 份简历，一个面试都没有？先别改简历。",
            "beats": [
                {"sec": "0-3", "line": "钩子：不是简历差，是你投的岗位和你做的事对不上", "shot": "正面口播，近景"},
                {"sec": "3-15", "line": "节拍 1：举一个真实例子，说清「错配」长什么样", "shot": "手机录屏 + 画外音"},
                {"sec": "15-35", "line": "节拍 2：给一个 3 步自检法", "shot": "白板/字幕卡"},
                {"sec": "35-50", "line": "节拍 3：告诉他改完怎么验证", "shot": "口播 + 字幕"},
            ],
            "cta": "评论区打「自检」，我把那张表发你",
            "titles": [
                "投了80份简历没回音，问题真不在简历",
                "求职最怕的不是没经验，是错配",
                "HR 3秒筛掉你，就因为这个",
                "改简历之前，先做这3步",
                "为什么你越投越没信心",
            ],
            "hashtags": ["#求职", "#简历", "#面试", "#应届生"],
            "shotlist": ["正面口播 3 镜", "录屏 2 段", "字幕卡 2 张", "结尾引导 1 镜"],
        }
    brief_text = json.dumps(brief, ensure_ascii=False)
    return call_llm(load_prompt("02_script.md"), f"选题：{topic}\n受众简报：{brief_text}")


def review(topic: str, script: dict, mock: bool) -> dict:
    if mock:
        return {"hook": 7.5, "originality": 7.0, "brand_fit": 8.0, "advice": "钩子可以更具体，把「80 份」换成更狠的数字"}
    return call_llm(load_prompt("03_review.md"), f"选题：{topic}\n脚本：{json.dumps(script, ensure_ascii=False)}")


def total_score(r: dict) -> float:
    vals = [float(r.get(k, 0) or 0) for k in ("hook", "originality", "brand_fit")]
    return round(sum(vals) / len(vals), 1)


# ────────────────────────── 落盘 ──────────────────────────

def slugify(s: str, n: int) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", s).strip("-")
    return f"{n:02d}_{s[:24]}"


def write_script(idx: int, topic: str, brief: dict, script: dict, rev: dict) -> Path:
    path = OUT / "scripts" / f"{slugify(topic, idx)}.md"
    lines = [f"# {topic}", "", f"> 生成时间：{datetime.now():%Y-%m-%d %H:%M}", ""]
    lines += ["## 受众简报", f"- 受众：{brief.get('audience','')}",
              f"- 痛点：{brief.get('pain','')}", f"- 切入角度：{brief.get('angle','')}", ""]
    lines += ["## 钩子（前 3 秒）", script.get("hook", ""), ""]
    lines += ["## 节拍"]
    for b in script.get("beats", []):
        lines += [f"- **{b.get('sec','')}** {b.get('line','')}", f"  - 画面：{b.get('shot','')}"]
    lines += ["", "## CTA", script.get("cta", ""), ""]
    lines += ["## 标题 5 版"] + [f"{i}. {t}" for i, t in enumerate(script.get("titles", []), 1)] + [""]
    lines += ["## 标签", " ".join(script.get("hashtags", [])), ""]
    lines += ["## 分镜清单"] + [f"- {s}" for s in script.get("shotlist", [])] + [""]
    lines += ["## AI 质检", f"- 钩子力 {rev.get('hook','-')}｜原创度 {rev.get('originality','-')}｜品牌契合 {rev.get('brand_fit','-')}",
              f"- 均分 **{total_score(rev)}**", f"- 建议：{rev.get('advice','')}"]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_report(rows: list[dict], mock: bool) -> Path:
    lines = ["# 本周内容流水线周报", "", f"生成时间：{datetime.now():%Y-%m-%d %H:%M}", "",
             f"模式：{'MOCK（未调用模型）' if mock else MODEL}", "",
             "| # | 选题 | 钩子力 | 原创度 | 品牌契合 | 均分 |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['idx']} | {r['topic']} | {r['hook']} | {r['originality']} | {r['brand_fit']} | {r['total']} |")
    avg = sum(r["total"] for r in rows) / max(len(rows), 1)
    lines += ["", f"平均分：**{avg:.1f}**（阈值 {THRESHOLD}，低于阈值会被要求重写一次）"]
    path = OUT / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ────────────────────────── 主流程 ──────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="不调用 API，用模板数据跑通流程")
    ap.add_argument("--topics", default=str(ROOT / "topics.txt"))
    args = ap.parse_args()

    topics = [t.strip() for t in Path(args.topics).read_text(encoding="utf-8").splitlines()
              if t.strip() and not t.startswith("#")]
    if not topics:
        print("topics.txt 里没有选题")
        return 1

    (OUT / "scripts").mkdir(parents=True, exist_ok=True)
    rows = []
    print(f"共 {len(topics)} 个选题，模式：{'MOCK' if args.mock else MODEL}\n")

    for i, topic in enumerate(topics, 1):
        print(f"[{i}/{len(topics)}] {topic}")
        brief = expand_topic(topic, args.mock)
        script = make_script(topic, brief, args.mock)
        rev = review(topic, script, args.mock)
        score = total_score(rev)

        if score < THRESHOLD:
            print(f"    质检 {score} < {THRESHOLD}，按建议重写一次…")
            brief = {**brief, "rewrite_hint": rev.get("advice", "")}
            script = make_script(topic, brief, args.mock)
            rev2 = review(topic, script, args.mock)
            if total_score(rev2) >= score:
                rev = rev2
                score = total_score(rev2)

        path = write_script(i, topic, brief, script, rev)
        print(f"    均分 {score} → {path.relative_to(ROOT)}")
        rows.append({"idx": i, "topic": topic, "hook": rev.get("hook", 0),
                     "originality": rev.get("originality", 0), "brand_fit": rev.get("brand_fit", 0), "total": score})

    report = write_report(rows, args.mock)
    print(f"\n完成，周报：{report.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:
        print(f"错误：{e}")
        sys.exit(2)
