<script setup lang="ts">
/**
 * 口碑学校 · 支撑度核验（对齐旧版 support.html）：
 * - 统计 chips：小学 59 所（有支撑/部分支撑）+ 初中 53 所（有支撑/部分支撑）
 * - 判定逻辑说明（信号类型 + 两档判定 + 初中差异）
 * - 有支撑/部分支撑明细表（小学 7 列 / 初中 7 列，按区排序）
 * - 数据来自 data/*.json 真源 + @gz/shared 格式化
 */
import { computed, ref } from 'vue';
import {
  formatPrimarySignals,
  formatMiddleSignals,
  formatXiaoshengchuBrief,
  type Tier1School,
} from '@gz/shared';
import { tier1Schools, middleTier1Schools, xiaoshengchuOf } from '../data';

const stage = ref<'primary' | 'middle'>('primary');

interface Row {
  name: string;
  district: string;
  cols: string[];
  basis?: string;
}

function fmtCells(s: Tier1School, stage: 'primary' | 'middle'): string[] {
  const rows = stage === 'primary' ? formatPrimarySignals(s) : formatMiddleSignals(s);
  const pick = (label: string) => rows.find((r) => r.label === label)?.value ?? '未查到';
  if (stage === 'primary') {
    // 出口机制列改由全量 xiaoshengchu 真源提供（全等匹配，跨区同名按 s.district 消歧）
    const chulu = formatXiaoshengchuBrief(xiaoshengchuOf(s.name, s.district));
    return [chulu, pick('教育集团'), pick('2026班数'), pick('学位预警'), pick('省一级')];
  }
  return [pick('中考成绩'), pick('示范性高中'), pick('教育集团'), pick('建校年份'), pick('指标到校')];
}

function buildRows(schools: Tier1School[], curStage: 'primary' | 'middle'): { full: Row[]; part: Row[]; none: Row[] } {
  const full: Row[] = [];
  const part: Row[] = [];
  const none: Row[] = [];
  for (const s of schools) {
    const r: Row = { name: s.name, district: s.district ?? '—', cols: fmtCells(s, curStage), basis: s.conclusion_basis };
    if (s.conclusion === '有支撑') full.push(r);
    else if (s.conclusion === '部分支撑') part.push(r);
    else none.push(r);
  }
  const by = (a: Row, b: Row) => a.district.localeCompare(b.district, 'zh') || a.name.localeCompare(b.name, 'zh');
  full.sort(by);
  part.sort(by);
  return { full, part, none };
}

const primary = buildRows(tier1Schools, 'primary');
const middle = buildRows(middleTier1Schools, 'middle');
const cur = computed(() => (stage.value === 'primary' ? primary : middle));

const chips = computed(() => {
  const c = cur.value;
  const full = c.full.length;
  const part = c.part.length;
  const none = c.none.length;
  return { total: full + part + none, full, part, none };
});

const summaryText = computed(() => {
  const c = cur.value;
  return `有支撑 ${c.full.length} · 部分支撑 ${c.part.length}${c.none.length ? ` · 不支撑 ${c.none.length}` : ''}`;
});
</script>

<template>
  <section>
    <div class="toolbar">
      <button class="chip" :class="{ active: stage === 'primary' }" @click="stage = 'primary'">
        小学 {{ primary.full.length + primary.part.length + primary.none.length }} 所
      </button>
      <button class="chip" :class="{ active: stage === 'middle' }" @click="stage = 'middle'">
        初中 {{ middle.full.length + middle.part.length + middle.none.length }} 所
      </button>
      <span class="summary">{{ summaryText }}</span>
    </div>

    <div class="intro">
      <p>广州从不公布逐校升学率、不做学校排名。所谓"口碑学校"是民间共识标签，本页用各区教育局官方文件与公开信息里可核验的客观信号，逐个判定"支撑度"：有支撑 / 部分支撑 / 不支撑。判定反映证据充分度，不等于办学水平；标签均为民间口径，非官方评价。</p>
      <p class="note">独立法人挂牌校（借用品牌但成绩未达标/无成绩证据）不计入口碑学校（地图上以虚线点标注）；独立法人合作校（借用品牌/托管，成绩达第一梯队的，如铁英、清湾）计入口碑，法人关系见详情页"品牌关联"板块。</p>
    </div>

    <div class="meta">
      <span class="chip2">小学：7 区 {{ primary.full.length + primary.part.length + primary.none.length }} 所网传公办小学</span>
      <span class="chip2 red"><b>有支撑 {{ primary.full.length }}</b> 所</span>
      <span class="chip2 amber"><b>部分支撑 {{ primary.part.length }}</b> 所</span>
      <span class="chip2">初中：7 区 {{ middle.full.length + middle.part.length + middle.none.length }} 所网传初中</span>
      <span class="chip2 red"><b>有支撑 {{ middle.full.length }}</b> 所</span>
      <span class="chip2 amber"><b>部分支撑 {{ middle.part.length }}</b> 所</span>
    </div>

    <div class="rule">
      <div class="block-title">判定逻辑</div>
      <div class="rule-cards">
        <div class="rule-card">
          <h3>小学 · 四类 A 层客观信号</h3>
          <ul>
            <li><b>出口结构</b>：小升初派位分组 / 对口直升（区教育局每年公布，可逐校查证）</li>
            <li><b>教育集团身份</b>：区属集团核心校 / 成员校</li>
            <li><b>招生规模</b>：2026 计划班数 / 人数</li>
            <li><b>学位预警</b>：教育局发布的学位供给预警名单</li>
          </ul>
          <p class="rule-note">不采信：升学率数字、学位房价格、自媒体口碑（无官方出处）；"省一级"为 2005 年停评的历史称号，仅辅助参考。</p>
        </div>
        <div class="rule-card">
          <h3>初中 · 五类信号</h3>
          <ul>
            <li><b>中考成绩</b>：网传喜报/家长汇总（2018 年起官方禁止公布，须注明年份口径）</li>
            <li><b>示范性高中</b>：国家级 / 市级示范性称号（官方名单）</li>
            <li><b>教育集团</b>：省市属 / 区属集团核心校或成员校</li>
            <li><b>建校年份</b>：判断"名号先行"的新校区与老牌强校</li>
            <li><b>指标到校</b>：名额分配（指标到校）录取记录，官方文件可溯</li>
          </ul>
          <p class="rule-note">有支撑 = 至少 1 项硬指标有公开可溯来源；部分支撑 = 有明确办学地位信号但缺硬数据。</p>
        </div>
      </div>
    </div>

    <div v-if="cur.none.length" class="note-block">
      另有 {{ cur.none.length }} 所网传学校判定"不支撑"（仅民间口碑、无官方信号），不计入下表。
    </div>

    <div class="block-title">有支撑的 {{ cur.full.length }} 所（{{ stage === 'primary' ? '小学' : '初中' }}）</div>
    <div class="tbl-wrap">
      <table>
        <thead>
          <tr>
            <th>学校</th><th>区</th>
            <template v-if="stage === 'primary'">
              <th>出口机制</th><th>教育集团</th><th>2026班数</th><th>学位预警</th><th>省一级</th>
            </template>
            <template v-else>
              <th>中考成绩</th><th>示范性高中</th><th>教育集团</th><th>建校年份</th><th>指标到校</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in cur.full" :key="'f' + r.name">
            <td class="school">{{ r.name }}</td><td>{{ r.district }}</td>
            <td v-for="c in r.cols" :key="c">{{ c }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="block-title">部分支撑的 {{ cur.part.length }} 所（{{ stage === 'primary' ? '小学' : '初中' }}）</div>
    <div class="tbl-wrap">
      <table>
        <thead>
          <tr>
            <th>学校</th><th>区</th>
            <template v-if="stage === 'primary'">
              <th>出口机制</th><th>教育集团</th><th>2026班数</th><th>学位预警</th><th>判定依据</th>
            </template>
            <template v-else>
              <th>中考成绩</th><th>示范性高中</th><th>教育集团</th><th>建校年份</th><th>指标到校</th><th>判定依据</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in cur.part" :key="'p' + r.name">
            <td class="school">{{ r.name }}</td><td>{{ r.district }}</td>
            <td v-for="c in r.cols" :key="c">{{ c }}</td>
            <td class="basis">{{ r.basis }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer>
      <p>数据来源：各区教育局 2026 年招生细则 / 派位分组表 / 集团化办学名单 / 学位预警文件 + 网传喜报（初中，注明年份与口径，非官方）。完整核验报告见项目 <code>docs/</code> 目录。</p>
      <p>口径说明：越秀 2026 未单独公布分组表（以 2023 版为基线）；荔湾 / 白云 / 黄埔 / 番禺部分集团成员名单不完整；初中若干集团新校区中考数据未公布——缺口均已标注"未查到"，未用第三方数字填充。</p>
    </footer>
  </section>
</template>

<style scoped>
.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 14px; }
.chip {
  border: 1px solid #d6d4cc; background: #fff; color: #1a1b1c;
  border-radius: 999px; padding: 6px 14px; font-size: 13px; cursor: pointer;
}
.chip.active { background: #3a5396; border-color: #3a5396; color: #fff; }
.summary { font-size: 12px; color: #6b7280; margin-left: 8px; }

.intro { background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; padding: 14px 16px; margin-bottom: 10px; }
.intro p { font-size: 13px; line-height: 1.7; color: #3a3f47; }
.intro .note { font-size: 12px; color: #6b7280; margin-top: 8px; }

.meta { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.chip2 {
  font-size: 12px; color: #3a3f47; background: #fff;
  border: 1px solid #e4e3dd; border-radius: 999px; padding: 3px 12px;
}
.chip2 b { font-weight: 700; }
.chip2.red { color: #e11d48; border-color: rgba(225,29,72,0.35); background: rgba(225,29,72,0.05); }
.chip2.amber { color: #b45309; border-color: rgba(245,158,11,0.4); background: rgba(245,158,11,0.08); }

.block-title { font-size: 14px; font-weight: 700; margin: 18px 0 8px; }
.rule { margin-bottom: 6px; }
.rule-cards { display: flex; flex-wrap: wrap; gap: 12px; }
.rule-card {
  flex: 1 1 340px; min-width: 0; background: #fff;
  border: 1px solid #e4e3dd; border-radius: 14px; padding: 12px 16px;
}
.rule-card h3 { font-size: 13px; font-weight: 700; margin-bottom: 6px; }
.rule-card ul { margin: 0 0 0 18px; font-size: 12.5px; color: #3a3f47; line-height: 1.8; }
.rule-card .rule-note { font-size: 12px; color: #6b7280; margin-top: 8px; line-height: 1.6; }

.note-block {
  background: #fdf3e3; border: 1px solid rgba(245,158,11,0.4); color: #8a5a00;
  border-radius: 12px; padding: 10px 14px; font-size: 12.5px; margin: 12px 0;
}

.tbl-wrap { overflow-x: auto; background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; }
table { width: 100%; border-collapse: collapse; font-size: 12.5px; min-width: 720px; }
thead th {
  text-align: left; font-size: 11.5px; color: #6b7280; font-weight: 600;
  padding: 10px 12px; border-bottom: 1px solid #e4e3dd; white-space: nowrap; background: #fafaf7;
}
tbody td { padding: 9px 12px; border-bottom: 1px solid rgba(34,38,46,0.07); vertical-align: top; }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: #f8f9fb; }
td.school { font-weight: 600; white-space: nowrap; }
td.basis { color: #6b7280; }

footer { margin-top: 18px; padding-top: 14px; border-top: 1px solid #e4e3dd; font-size: 12px; color: #6b7280; line-height: 1.8; }
footer code { background: #e8e7e1; border-radius: 4px; padding: 1px 5px; }
</style>
