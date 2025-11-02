#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量解析《气候小卫士》课程文档，自动生成 lesson-02~25.json
"""
import json
import re
from pathlib import Path

DOCS_DIR   = Path(__file__).with_name('..') / 'docs'
ASSETS_DIR = Path(__file__).with_name('..') / 'assets'
TARGET_DIR = Path(__file__).with_name('..') / 'climate-guardian' / 'public' / 'slides'

def parse_lessons(md_text: str):
    """按“第 N 课”分段，返回 list[dict] """
    # 分割课程块
    chunks = re.split(r'(?=^#### 第\d+课：)', md_text, flags=re.M)
    lessons = []
    for chk in chunks:
        if not chk.strip():
            continue
        # 标题
        title_match = re.search(r'^#### (第\d+课：(.+?))（', chk, re.M)
        if not title_match:
            continue
        full_title = title_match.group(1).strip()
        title_only = title_match.group(2).strip()
        lesson_num = int(re.search(r'\d+', full_title).group())

        # 知识点：学习目标/知识要点 下的列表
        knowledge = re.findall(r'^-\s+(.+?)$', chk, re.M)

        # 互动问题：思考题/互动 下的列表
        questions = re.findall(r'^\d+\.\s+(.+?)$', chk, re.M)

        lessons.append({
            'lesson_num': lesson_num,
            'full_title': full_title,
            'title': title_only,
            'knowledge': knowledge,
            'questions': questions
        })
    return lessons

def build_slide_json(lesson: dict):
    """构造与 lesson-01.json 同格式 """
    slides = [
        {'type': 'title', 'content': lesson['full_title']},
        {'type': 'text', 'content': '学习目标', 'data': lesson['knowledge']},
    ]
    # 如有互动问题
    if lesson['questions']:
        slides.append({
            'type': 'text',
            'content': '思考题',
            'question': lesson['questions']
        })

    # 自动关联资源
    n = lesson['lesson_num']
    csv_candidates = list(ASSETS_DIR.glob(f'data/lesson-{n:02d}-*.csv'))
    if csv_candidates:
        slides.append({
            'type': 'chart',
            'content': '数据可视化',
            'data': f'assets/data/{csv_candidates[0].name}'
        })
    png_candidates = list(ASSETS_DIR.glob(f'images/lesson-{n:02d}-*.png'))
    if png_candidates:
        slides.append({
            'type': 'chart',
            'content': '关键图表',
            'data': f'assets/images/{png_candidates[0].name}'
        })
    mp4_path = ASSETS_DIR / 'videos' / f'lesson-{n:02d}-intro.mp4'
    if mp4_path.exists():
        slides.append({
            'type': 'video',
            'content': '课程引入',
            'src': f'assets/videos/{mp4_path.name}'
        })

    return {
        'title': lesson['full_title'],
        'slides': slides
    }

def main():
    md_file = DOCS_DIR / '2-课程详细内容.md'
    if not md_file.exists():
        print('❌ 未找到', md_file)
        return

    md_text = md_file.read_text(encoding='utf-8')
    lessons = parse_lessons(md_text)
    print(f'📚 共解析出 {len(lessons)} 课')

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    for ls in lessons:
        if ls['lesson_num'] == 1:
            continue  # 跳过第1课
        payload = build_slide_json(ls)
        out = TARGET_DIR / f'lesson-{ls["lesson_num"]:02d}.json'
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'✅ 生成 {out}')

if __name__ == '__main__':
    main()