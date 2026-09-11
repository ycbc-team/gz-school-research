# -*- coding: utf-8 -*-
"""越秀 tier1 6 所 source 更新：2023 分组表 → 2026 官方口径。

事实核验（2026-09-10）：
- 2026 官方《招生工作实施细则》（post_10790590，2026-04-28）确认：对口直升（铁一→铁一小学、
  培正→培正小学、育才→育才学校、5 所九年一贯）与分组电脑派位，执信统一派位校区为执信路校区；
  分组保持相对稳定。
- 2026 分组表与 2022（post_8301356）/2023 分组表一致（11 组，每组 10 所初中）；唯一变化：
  第十一组"矿泉中学"→"培正矿泉学校"（2026 新校，瑶台改造，不涉 tier1 6 所）。
- 6 所 tier1 涉及组：一（东风东路、农林下路）、四（小北路）、五（培正、铁一）、七（文德路），
  组内容与 2023 一致，feed 不变，仅刷新来源标注。

用法：python3 scripts/primary/refresh_yuexiu_xiaoshengchu.py
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DETAIL = 'https://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/jyjwj/content/post_10790590.html'
PLAN = 'https://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/zswd/content/post_10790618.html'
GROUP2022 = 'http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/zswd/content/post_8301356.html'

# name -> (group, note)
FIX = {
    '东风东路小学': ('第一组', '2026年越秀区官方《招生工作实施细则》（2026-04-28，post_10790590）确认分组电脑派位保持稳定，组别与2022/2023官方分组表（post_8301356）一致：第一组=东风东路/农林下路/育才/水荫路小学，组内10所初中；执信统一派位校区为执信路校区（2026招生计划post_10790618）。'),
    '农林下路小学': ('第一组', '2026年越秀区官方细则（2026-04-28）确认分组保持稳定，第一组=东风东路/农林下路/育才/水荫路小学（与2022/2023官方分组表一致）；执信统一执信路校区。'),
    '小北路小学': ('第四组', '2026年越秀区官方细则（2026-04-28）确认分组保持稳定，第四组=桂花岗/登峰/小北路小学（与2022/2023官方分组表一致）；组内含二中、广大附中、执信本部、广东侨中。'),
    '文德路小学': ('第七组', '2026年越秀区官方细则（2026-04-28）确认分组保持稳定，第七组=八旗二马路/珠光路/清水濠/秉正/文德路/雅荷塘/豪贤路/广中路小学（与2022/2023官方分组表一致）；组内含省实、铁一、培正、三中。'),
    '东山培正小学': ('第五组', '2026年越秀区官方细则（2026-04-28）确认：培正中学面向培正小学招收对口直升生（直升即放弃派位）；第五组=署前路/八一实验/东山实验/培正/铁一/杨箕/五羊小学，组内含省实、铁一、培正、七中、16中（与2022/2023官方分组表一致）。'),
    '铁一小学': ('第五组', '2026年越秀区官方细则（2026-04-28）确认：铁一中学面向铁一小学招收对口直升生（直升即放弃派位）；第五组=署前路/八一实验/东山实验/培正/铁一/杨箕/五羊小学，组内含铁一、省实、培正、七中、16中（与2022/2023官方分组表一致）。'),
}

def main():
    targets = [
        os.path.join(ROOT, 'data/primary/tier1_schools_yuexiu_liwan.json'),
        os.path.join(ROOT, 'data/primary/tier1_schools_all.json'),
    ]
    for path in targets:
        d = json.load(open(path, encoding='utf-8'))
        schools = d['districts']['越秀区']['schools']
        patched = 0
        for s in schools:
            x = s.get('xiaoshengchu')
            if not x:
                continue
            for key, (group, note) in FIX.items():
                if key in s['name']:
                    x['group'] = group
                    x['source_url'] = DETAIL
                    x['source_note'] = note
                    patched += 1
                    break
        json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f'{os.path.basename(path)}: patched={patched}/6')

if __name__ == '__main__':
    main()
