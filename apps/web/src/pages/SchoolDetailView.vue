<script setup lang="ts">
/**
 * 学校详情页（三学段统一）：
 * - 小学：法人核验 + 小升初机制 + 2026 招生计划
 * - 初中：法人核验 + 升学通道（名额分配 21 校区 + 自招/体育/艺术 + 第二批次录取分数）
 * - 高中：分类/校区/出口数据（录取线·高分段·特控率，网传口径标注）+ 名额分配覆盖初中
 * 数据真源：data/ 各 JSON（apps/web/src/data 加载），链路数据为 2026 官方发布。
 */
import { computed, ref, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import {
  buildDetailModel, normName,
  type SchoolStage,
} from '@gz/shared';
import {
  repository, entities, matchEnrollment,
  middleQuotaSummary, middleEnrollmentsOf, middleEnrollmentGroups, xiaoshengchuOf, schoolBadges, scoresOfSchool,
  isComprehensive, groupOfSchool, resolveSchoolIdOf,
  type BrandUnit,
  innovationAwards,
  chuangkeAwards,
  scienceLiteracyAwards,
  techSportsAwards,
  scienceExperimentAwards,
  yueyunbeiAwards,
  specialtySchools,
  civilizedCampusSchoolIds,
} from '../data';
import LinkagePanel from '../components/LinkagePanel.vue';

/** 招生说明：数据层（@gz/shared createEnrollmentApi）已把番禺「见说明N」平铺为说明内容，此处原样展示。 */
type NoteSeg = { text: string };
const noteSegs = computed<NoteSeg[]>(() => (enrollment.value?.note ? [{ text: enrollment.value.note }] : []));
const props = defineProps<{ name: string; stage?: string }>();
const route = useRoute();
const schoolName = computed(() => decodeURIComponent(props.name || ''));
/** URL 有 id 优先；无 id 时从实体表解析，保证深链与地图链接一致。 */
const schoolId = computed(() => {
  if (typeof route.query.id === 'string' && route.query.id) return route.query.id;
  return repository.resolveSchoolIdOf(schoolName.value) || '';
});
const router = useRouter();
const STAGE_LABEL: Record<SchoolStage, string> = { primary: '小学部', middle: '初中部', high: '高中部' };

/** Web 与小程序统一消费 shared 详情模型；本组件仅保留路由与渲染适配。 */
const probe = computed(() => buildDetailModel('primary', schoolName.value, repository, schoolId.value));
const availableStages = computed(() => probe.value.availableStages);
const activeStage = ref<SchoolStage>('primary');
function resolveStage(): SchoolStage {
  const requested = route.query.stage as string | undefined;
  return requested && availableStages.value.includes(requested as SchoolStage)
    ? requested as SchoolStage : availableStages.value[0] || 'primary';
}
watch([schoolName, () => route.query.stage, schoolId], () => { activeStage.value = resolveStage(); }, { immediate: true });
const model = computed(() => buildDetailModel(activeStage.value, schoolName.value, repository, schoolId.value));
const stage = computed(() => model.value.stage);
function switchStage(next: SchoolStage) {
  router.replace({ path: `/school/${encodeURIComponent(schoolName.value)}`, query: { stage: next, ...(schoolId.value ? { id: schoolId.value } : {}) } });
}
function goBack() { window.history.length > 1 ? router.back() : router.push('/map'); }
function viewOnMap() { router.push({ path: '/map', query: { focus: schoolId.value || schoolName.value } }); }

const stageLabel = computed(() => model.value.stageLabel);
const districtOf = computed(() => model.value.district);
const poi = computed(() => model.value.poi);
const badges = computed(() => model.value.badges);
const headText = computed(() => model.value.headText);
const legalEntityText = computed(() => model.value.legalEntityText);
const enrollment = computed(() => model.value.enrollment);
const nature = computed(() => model.value.nature);
const feedJuniors = computed(() => model.value.feedJuniors);
const feedGap = computed(() => model.value.feedGap);
const feedRows = computed(() => model.value.feedRows);
const enrollNote = computed(() => model.value.enrollNote);
const admissionRows = computed(() => model.value.admissionRows);
const gaokaoRows = computed(() => model.value.gaokaoRows);
const brandCard = computed(() => model.value.brandCard);
const brandCardUseful = computed(() => model.value.brandCardUseful);
const multiCampusCard = computed(() => model.value.multiCampusCard);
const multiCampusCardUseful = computed(() => model.value.multiCampusCardUseful);
const campuses = computed(() => model.value.campuses);
/** 文明校园称号按当前 school_id 判定；创建先进学校明确标为创建培育，不与正式命名混淆。 */
const civilizedCampusHonors = computed(() => {
  if (!schoolId.value) return [];
  const levels = [
    ['national', '全国文明校园'],
    ['provincial', '广东省文明校园'],
    ['municipal', '广州市文明校园'],
    ['advanced', '广州市文明校园创建先进学校（储备）'],
  ] as const;
  return levels.filter(([key]) => (civilizedCampusSchoolIds[key] ?? []).includes(schoolId.value)).map(([, label]) => label);
});
/** 创新大赛获奖：按当前 school_id 查，有则展示金/银/铜（分学段分年份） */
const awardData = computed(() => innovationAwards[schoolId.value]?.innovation_awards?.stages?.[stage.value]);
/** 创客电视大赛官方只有小学组/中学组，中学组同时覆盖初中和高中。 */
const chuangkeStage = computed(() => stage.value === 'middle' || stage.value === 'high' ? 'secondary' : stage.value);
const chuangkeData = computed(() => chuangkeAwards[schoolId.value]?.chuangke_awards?.stages?.[chuangkeStage.value]);
const chuangkeGroupLabel = computed(() => chuangkeStage.value === 'secondary' ? '中学组（初中+高中）' : stageLabel.value);
const scienceLiteracyData = computed(() => scienceLiteracyAwards[schoolId.value]?.science_literacy_awards?.stages?.[stage.value]);
/** 科技体育教育竞赛：小学组及测向10-12岁→primary；中学组及测向15岁→secondary（初高合并）；测向18岁→high。
 *  高中详情页合并 secondary（中学组）+ high（测向18岁）两档。 */
const techSportsStage = computed(() => (stage.value === 'middle' ? 'secondary' : stage.value));
const techSportsData = computed(() => {
  const stages = techSportsAwards[schoolId.value]?.tech_sports_awards?.stages;
  if (!stages) return undefined;
  if (stage.value === 'high') {
    const merged: Record<string, { gold: number; silver: number; bronze: number }> = {};
    for (const key of ['secondary', 'high'] as const) {
      for (const [year, counts] of Object.entries(stages[key] || {})) {
        merged[year] = {
          gold: (merged[year]?.gold || 0) + counts.gold,
          silver: (merged[year]?.silver || 0) + counts.silver,
          bronze: (merged[year]?.bronze || 0) + counts.bronze,
        };
      }
    }
    return Object.keys(merged).length ? merged : undefined;
  }
  return stages[techSportsStage.value];
});
/** 科学实验大赛获奖：按当前 school_id 与学段直接查（2025 首届） */
const scienceExperimentData = computed(() => scienceExperimentAwards[schoolId.value]?.science_experiment_awards?.stages?.[stage.value]);
/** 粤韵杯获奖：按当前 school_id 与学段直接查（小学/初中/高中组），优胜奖不计数 */
const yueyunbeiData = computed(() => yueyunbeiAwards[schoolId.value]?.yueyunbei_awards?.stages?.[stage.value]);
const awardYears = computed(() => awardData.value ? Object.keys(awardData.value).sort().reverse() : []);
/** 赛事年份标签：从各赛事 compiled 聚合（school×stage×year 计数）推导全局年份，
 *  不再依赖 3.8MB 明细数据（gzip 738KB）——详情页只展示年份区间，明细由获奖页消费。 */
type AwardsIndex = Record<string, { [competition: string]: { stages: Record<string, Record<string, { gold: number; silver: number; bronze: number }>> } }>;
function competitionYearsLabel(data: AwardsIndex, competition: string) {
  const years = new Set<number>();
  for (const entry of Object.values(data)) {
    const comp = entry[`${competition}_awards`];
    if (!comp?.stages) continue;
    for (const byYear of Object.values(comp.stages)) {
      for (const y of Object.keys(byYear)) {
        const n = Number(y);
        if (Number.isFinite(n)) years.add(n);
      }
    }
  }
  const sorted = [...years].sort((a, b) => a - b);
  return sorted.length > 1 ? `${sorted[0]}-${sorted[sorted.length - 1]}` : (sorted[0] ? String(sorted[0]) : '');
}
const innovationYearsLabel = computed(() => competitionYearsLabel(innovationAwards, 'innovation'));
const chuangkeYearsLabel = computed(() => competitionYearsLabel(chuangkeAwards, 'chuangke'));
const scienceLiteracyYearsLabel = computed(() => competitionYearsLabel(scienceLiteracyAwards, 'science_literacy'));
const techSportsYearsLabel = computed(() => competitionYearsLabel(techSportsAwards, 'tech_sports'));
const scienceExperimentYearsLabel = computed(() => competitionYearsLabel(scienceExperimentAwards, 'science_experiment'));
const yueyunbeiYearsLabel = computed(() => competitionYearsLabel(yueyunbeiAwards, 'yueyunbei'));
/** 特色校称号（官方认定·省市各级）：按当前 school_id 或校名匹配 dist 聚合，展开 recognition 池 */
const specialtyEntry = computed(() => {
  const doc = specialtySchools;
  if (schoolId.value) {
    const byId = doc.schools.find((s) => s.ids.includes(schoolId.value));
    if (byId) return byId;
  }
  const n = normName(schoolName.value);
  return doc.schools.find((s) => normName(s.school) === n) || null;
});
/** 从 note.t 混合备注中提取"传承项目/艺术项目"具体内容（区推断/脚本来源/公示时间等采集备注丢弃） */
function extractArtsProject(noteT?: string): string | null {
  if (!noteT) return null;
  const parts = noteT.split(/[;；]/).map((s) => s.trim()).filter(Boolean);
  const found: string[] = [];
  for (const p of parts) {
    if (p.startsWith('传承项目:')) {
      const v = p.slice('传承项目:'.length).trim();
      if (v) found.push('传承项目：' + v);
    } else if (p.startsWith('艺术项目:')) {
      const v = p.slice('艺术项目:'.length).trim();
      if (v) found.push('艺术项目：' + v);
    }
  }
  return found.length ? found.join('；') : null;
}
/** 称号级别排序权重：国家级 > 省级 > 市级 */
const LEVEL_ORDER: Record<string, number> = { '国家级': 0, '省级': 1, '市级': 2 };
const specialtyRows = computed(() => {
  const entry = specialtyEntry.value;
  if (!entry || !entry.rec.length) return [];
  return entry.rec
    .map((i) => {
      const r = specialtySchools.recognition[i];
      if (!r) return null;
      const note = entry.notes?.find((x) => x.i === i);
      return { ...r, artsProject: extractArtsProject(note?.t) };
    })
    .filter((x): x is NonNullable<typeof x> => !!x)
    .filter((r) => !r.stage || r.stage === stage.value)
    .sort((a, b) => (LEVEL_ORDER[a.level] ?? 99) - (LEVEL_ORDER[b.level] ?? 99));
});
/** 初中 tab：2026 招生计划（一校多规则：同一初中可对应多区/多机制入学，逐条渲染），按当前学段 POI school_id 外键查 */
const middleEnrolls = computed(() => {
  if (stage.value !== 'middle') return [];
  return middleEnrollmentsOf(schoolId.value || null) || [];
});
/** 派位组成员行 Badge：dist groups 组名（如「电脑派位第4组」）；组缺省时兜底 */
function groupNameOf(gid?: string | null): string {
  return (gid ? middleEnrollmentGroups[gid]?.name : null) || '组内可填报';
}
/** 机制块线性排列：每机制一块（徽章 + 招生服务范围/招生说明 + 该机制生源小学）。
 * 顺序：对口直升(zhi_sheng) → 单校划片(single_zone) → 多校电脑派位(group_paidui) → 电脑派位(single_paidui)
 * → 自主招生(min_zi_zhu)（用户：先直升后派位）。
 * 同区同机制多条（多组派位）合并为一块；同校多机制并存时 plan_classes 是全校总计划，
 * 徽章不重复显示班数（避免 9+9=18 误读），由 totalPlanOfMulti 展示一次。
 * 区 Badge 仅在同机制跨区（天河/越秀并存的 2 所）时才显示，其余场景一律不显示（用户：删海珠区 Badge）。
 * group_paidui 与 single_zone 同样展示 scope（招生服务范围/对口小学）与 mechanism_note（招生说明），
 * 但跳过纯组名类备注（组名已由行 tag 展示，避免「海珠区…第1组」重复）。 */
/** 派位组子块：按 group_id（多校派位）或单条 enroll（直升/划片/电脑派位）拆分；
 *  每个子块内依次展示：服务范围 → 生源小学 → 招生说明。 */
type SubBlock = {
  key: string;
  groupName: string;            // 派位组名（如「电脑派位第4组」）；直升/划片/电脑派位为空
  rows: { name: string; ids: string[] }[];
  textScopes: string[];
  notes: string[];
  loseText: string | null;      // 电脑派位未中警示
};
type MechBlock = { district: string; mech: string; label: string; showDistrict: boolean; subBlocks: SubBlock[] };
/** 纯组名/纯机制名备注跳过展示（组名已由子块标题呈现）：「海珠区…第1组」「荔湾区1组电脑派位」「电脑派位」 */
function isRedundantNote(note: string): boolean {
  const n = note.trim();
  if (n === '电脑派位') return true;
  if (/[第]?\s*[一二三四五六七八九十\d]+\s*组\s*$/.test(n)) return true;
  if (/^[^；。]{0,14}电脑派位\s*$/.test(n)) return true;
  return false;
}
const MECH_ORDER = ['zhi_sheng', 'single_zone', 'group_paidui', 'single_paidui', 'min_zi_zhu'];
const mechanismBlocks = computed<MechBlock[]>(() => {
  if (stage.value !== 'middle') return [];
  const byKey = new Map<string, MechBlock>();
  const order: string[] = [];
  const pushRow = (sub: SubBlock, name: string, ids: string[]) => {
    if (!sub.rows.some((r) => r.name === name)) sub.rows.push({ name, ids });
  };
  const pushText = (arr: string[], v: string) => {
    if (v && !arr.includes(v)) arr.push(v);
  };
  for (const m of middleEnrolls.value) {
    const key = `${m.district}|${m.record.mechanism}`;
    let b = byKey.get(key);
    if (!b) { b = { district: m.district, mech: m.record.mechanism, label: m.mechanismDef.label, showDistrict: false, subBlocks: [] }; byKey.set(key, b); order.push(key); }
    const rec = m.record;
    // 多校电脑派位：同一 group_id 合并为一个子块，组名作子块标题
    if (b.mech === 'group_paidui' && rec.group_id) {
      let sub = b.subBlocks.find((s) => s.key === rec.group_id);
      if (!sub) {
        sub = { key: rec.group_id, groupName: groupNameOf(rec.group_id), rows: [], textScopes: [], notes: [], loseText: null };
        b.subBlocks.push(sub);
      }
      const g = middleEnrollmentGroups[rec.group_id];
      const pid = g?.primaryIds ?? {};
      for (const p of Object.keys(pid)) pushRow(sub, p, pid[p] ?? []);
      // 生源小学：直接遍历 scope_school_ids 解析键 → 可点击行（973b1b4 口径，合并保留）。
      // 不做 scope 原文分段精确匹配：原文段常含括号注释（如「（除民强村、新兴村外）」）、换行、
      // 括号内顿号（如「（总校区、北校区）」），与解析键不一致会漏行；scope_school_ids 是解析器
      // 输出的权威「段→school_ids」结构。键本身即 scope 原文片段，按原文出现顺序展示（未命中的兜底排后）。
      const smap = rec.scope_school_ids ?? {};
      const scopeText = rec.scope ?? '';
      const orderedKeys = Object.keys(smap).sort((a, b) => {
        const ia = scopeText.indexOf(a), ib = scopeText.indexOf(b);
        return (ia === -1 ? 1e9 : ia) - (ib === -1 ? 1e9 : ib);
      });
      for (const p of orderedKeys) pushRow(sub, p, smap[p] ?? []);
      if (rec.scope) pushText(sub.textScopes, rec.scope.trim());
      if (rec.mechanism_note && !isRedundantNote(rec.mechanism_note)) pushText(sub.notes, rec.mechanism_note);
    } else {
      // 对口直升 / 单校划片 / 电脑派位 / 自主招生：每条 enroll 一个子块，不设组标题
      const sub: SubBlock = {
        key: `enroll-${b.subBlocks.length}`,
        groupName: '',
        rows: [],
        textScopes: [],
        notes: [],
        loseText: (m.mechanismDef.can_lose && m.mechanismDef.lose_text) || null,
      };
      if (b.mech === 'single_zone') {
        // 直升小学：直接遍历 scope_school_ids 解析键（同上：不做 scope 原文分段匹配，
        // 原文段含括号注释/换行/括号内顿号会与解析键不一致导致漏行）；键按原文出现顺序展示
        const smap = rec.scope_school_ids ?? {};
        const scopeText = rec.scope ?? '';
        const orderedKeys = Object.keys(smap).sort((a, b) => {
          const ia = scopeText.indexOf(a), ib = scopeText.indexOf(b);
          return (ia === -1 ? 1e9 : ia) - (ib === -1 ? 1e9 : ib);
        });
        for (const p of orderedKeys) pushRow(sub, p, smap[p] ?? []);
      }
      if (rec.scope) pushText(sub.textScopes, rec.scope.trim());
      if (rec.mechanism_note) pushText(sub.notes, rec.mechanism_note);
      b.subBlocks.push(sub);
    }
  }
  const blocks = order.map((k) => byKey.get(k)!);
  blocks.sort((a, b2) => {
    const ia = MECH_ORDER.indexOf(a.mech), ib = MECH_ORDER.indexOf(b2.mech);
    if (ia !== -1 && ib !== -1) return ia - ib;
    if (ia !== -1) return -1;
    if (ib !== -1) return 1;
    return order.indexOf(`${a.district}|${a.mech}`) - order.indexOf(`${b2.district}|${b2.mech}`);
  });
  const mechDistricts = new Map<string, Set<string>>();
  for (const b of blocks) {
    if (!mechDistricts.has(b.mech)) mechDistricts.set(b.mech, new Set());
    mechDistricts.get(b.mech)!.add(b.district);
  }
  for (const b of blocks) b.showDistrict = (mechDistricts.get(b.mech)?.size ?? 1) > 1;
  return blocks;
});
/** 全校总计划班数（plan_classes 为一校多方式共用的总班数），统一展示在卡片标题右侧 */
const totalPlan = computed<number | null>(() => {
  if (stage.value !== 'middle') return null;
  for (const m of middleEnrolls.value) {
    if (m.record.plan_classes != null) return m.record.plan_classes;
  }
  return null;
});
/** 多校区法人行弹窗（与初中名额分配明细 RankingView 同款）：一个小学名 + school_ids → 弹窗选校区跳转 */
const campusPicker = ref<{ top: number; left: number; items: Array<{ id: string; name: string }> } | null>(null);
function openPrimaryPicker(row: { name: string; ids: string[] }, e: MouseEvent) {
  if (row.ids.length < 2) return;
  const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
  const w = 300;
  let left = r.left;
  if (left + w > window.innerWidth - 8) left = Math.max(8, window.innerWidth - w - 8);
  const entArr = entities.entities ?? (entities as unknown as any[]);
  campusPicker.value = { top: r.bottom + 6, left, items: row.ids.map((id) => ({ id, name: entArr.find((x: { school_id: string }) => x.school_id === id)?.name ?? id })) };
}
function closeCampusPicker() { campusPicker.value = null; }
function goCampus(item: { id: string; name: string }) {
  closeCampusPicker();
  router.push({ path: `/school/${encodeURIComponent(item.name)}`, query: { stage: 'primary', id: item.id } });
}

</script>

<template>
  <section class="detail">
    <button class="back" @click="goBack">← 返回</button>
    <button class="back" style="margin-left:12px;" @click="viewOnMap">在地图中查看</button>

    <header class="d-head">
      <h1>{{ schoolName }}</h1>
      <div class="badges">
        <span v-for="b in badges" :key="b.cls + b.text" class="badge" :class="b.cls">{{ b.text }}</span>
      </div>
      <p v-if="headText" class="d-sub">{{ headText }}</p>
    </header>

    <!-- 未收录点位：名字直达但无 POI 实体（如官方名单中的 7 区外学校），信息不可跳转、仅展示 -->
    <p v-if="!poi" class="not-included-card">该名称暂未收录到地图点位，以下信息来自官方名单 / 源数据，可能对应多个校区或位于七区之外，详情仅供展示、不可跳转。</p>

    <!-- 学部切换 tab（完中/多学部学校才显示） -->
    <nav v-if="availableStages.length > 1" class="stage-tabs">
      <button
        v-for="s in availableStages"
        :key="s"
        class="stage-tab"
        :class="{ on: stage === s }"
        @click="switchStage(s)"
      >{{ STAGE_LABEL[s] }}</button>
    </nav>

    <!-- 基本信息 -->
    <div class="card">
      <div class="card-title">基本信息</div>
      <div class="kv">
        <div class="kv-row"><span>学段</span><b>{{ stageLabel }}</b></div>
        <div class="kv-row"><span>所属区</span><b>{{ districtOf }}</b></div>
        <div v-if="brandCard?.brand" class="kv-row"><span>教育集团</span><b>{{ brandCard.brand }}</b></div>
        <div v-if="civilizedCampusHonors.length" class="kv-row specialty-row">
          <span>校园荣誉</span>
          <b><div v-for="honor in civilizedCampusHonors" :key="honor" class="specialty-line">{{ honor }}</div></b>
        </div>
        <div v-if="specialtyRows.length" class="kv-row specialty-row">
          <span>学校特色</span>
          <b>
            <div v-for="(r, idx) in specialtyRows" :key="idx" class="specialty-line">
              <a v-if="r.url" :href="r.url" target="_blank" rel="noopener noreferrer" class="specialty-link">
                {{ r.project }}<template v-if="r.artsProject">（{{ r.artsProject }}）</template>
              </a>
              <template v-else>
                {{ r.project }}<template v-if="r.artsProject">（{{ r.artsProject }}）</template>
              </template>
            </div>
          </b>
        </div>
      </div>
    </div>

    <!-- 小学 tab：招生计划 + 所在区小升初机制 -->
    <div v-if="stage === 'primary'" class="card">
      <div class="plan-head">
        <div class="card-title" style="margin-bottom:0;">招生计划（2026）</div>
        <div v-if="enrollment?.plan_classes != null" class="plan-total">计划 {{ enrollment.plan_classes }} 个班</div>
      </div>
      <div v-if="enrollment" class="kv">
        <div class="kv-row" v-if="enrollment.plan_count"><span>计划人数</span><b>{{ enrollment.plan_count }} 人</b></div>
        <div v-if="enrollment.zone" class="zone-block">
          <div class="zone-label">招生地段（对口）</div>
          <p>{{ enrollment.zone }}</p>
        </div>
        <div v-if="enrollment.note" class="zone-block">
          <div class="zone-label">招生说明</div>
          <p v-for="(seg, i) in noteSegs" :key="i">{{ seg.text }}</p>
        </div>
      </div>
      <p v-else class="empty">未在 2026 招生计划中匹配到招生地段（数据覆盖七区；分校区、新建校暂缺，后续补录）。</p>
    </div>

    <!-- 小学 tab：升学路线（对口初中 · 派位/直升） -->
    <div v-if="stage === 'primary' && (feedRows.length || feedGap || feedJuniors?.direct_feed)" class="card">
      <div class="card-title">升学路线（2026）</div>
      <p v-if="feedJuniors?.group" class="sub-note">分组：{{ feedJuniors.group }}</p>
      <p v-if="feedJuniors?.direct_feed" class="sub-note">直升：{{ feedJuniors.direct_feed }}</p>
      <div v-if="feedRows.length" class="feed-list">
        <div v-for="r in feedRows" :key="r.name" class="feed-item">
          <RouterLink v-if="r.poiName" :to="`/school/${encodeURIComponent(r.poiName)}?stage=middle`" class="feed-name">{{ r.name }}</RouterLink>
          <span v-else class="feed-name" style="color:#6b7280;">{{ r.name }}</span>
          <span v-if="r.summary" class="tag">{{ r.summary }}</span>
          <span v-else class="tag tag-dim">区属初中</span>
        </div>
      </div>
      <p v-if="feedGap" class="empty" :style="feedRows.length ? 'margin-top:8px;text-align:left;' : ''">{{ feedGap }}</p>
      <p v-if="feedJuniors?.source_note" class="sub-note" style="margin-top:8px;">{{ feedJuniors.source_note }}</p>
      <p v-if="feedRows.length" class="sub-note" style="margin-top:4px;">点击初中可查看该校升学通道详情。</p>
    </div>

    <!-- 初中 tab：招生计划（2026）：标题右侧统一放总班数；按机制分组 → 组内再按派位组拆子块 -->
    <div v-if="stage === 'middle'" class="card">
      <div class="plan-head">
        <div class="card-title" style="margin-bottom:0;">招生计划（2026）</div>
        <div v-if="totalPlan != null" class="plan-total">计划 {{ totalPlan }} 个班</div>
      </div>
      <p v-if="enrollNote" class="sub-note" style="margin-top:6px;">{{ enrollNote }}</p>

      <template v-if="middleEnrolls.length">
        <template v-for="(mb, mbi) in mechanismBlocks" :key="`${mb.district}-${mb.mech}`">
          <!-- 机制标签行 -->
          <div class="mech-row" :style="mbi ? 'margin-top:14px;' : 'margin-top:4px;'">
            <span v-if="mb.showDistrict" class="badge b-district">{{ mb.district }}</span>
            <span class="badge" :class="mb.mech">{{ mb.label }}</span>
          </div>

          <!-- 派位组子块：服务范围 → 生源小学 → 招生说明 -->
          <div v-for="sub in mb.subBlocks" :key="sub.key" class="sub-block">
            <div v-if="sub.groupName" class="sub-title">{{ sub.groupName }}</div>

            <div v-for="ts in sub.textScopes" :key="'s' + ts" class="zone-block">
              <div class="zone-label">服务范围</div>
              <p>{{ ts }}</p>
            </div>

            <div v-if="sub.rows.length" class="zone-block">
              <div class="zone-label">生源小学</div>
              <div class="feed-list">
                <div v-for="row in sub.rows" :key="row.name" class="feed-item">
                  <button v-if="row.ids.length > 1" class="feed-name campus-open" @click="openPrimaryPicker(row, $event)">{{ row.name }}</button>
                  <RouterLink v-else-if="row.ids.length === 1" :to="`/school/${encodeURIComponent(row.name)}?id=${row.ids[0]}&stage=primary`" class="feed-name">{{ row.name }}</RouterLink>
                  <span v-else class="feed-name">{{ row.name }}</span>
                </div>
              </div>
            </div>
            <!-- 招生说明：直升机制内去重只展示一条（官方同一来源）；「见说明N」已在数据层平铺 -->
            <div v-for="nt in sub.notes" :key="'n' + nt" class="zone-block">
              <div class="zone-label">招生说明</div>
              <p>{{ nt }}</p>
            </div>

            <div v-if="sub.loseText" class="lottery-warning">⚠️ {{ sub.loseText }}</div>
          </div>
        </template>
      </template>

      <p v-if="!middleEnrolls.length" class="empty">{{ nature === '民办' ? '暂无招生计划数据：2026 民办初中招生由区教育局统一组织（电脑摇号），以区教育局当年正式文件为准。' : '暂无招生计划数据：2026 公办初中招生计划表未收录本校，以区教育局当年正式文件为准。' }}</p>
    </div>

    <!-- 多校区生源小学：弹窗选校区（与初中名额分配明细同款） -->
    <Teleport to="body">
      <div v-if="campusPicker" class="campus-mask" @click="closeCampusPicker"></div>
      <div v-if="campusPicker" class="campus-pop" :style="{ top: campusPicker.top + 'px', left: campusPicker.left + 'px' }">
        <div class="campus-pop-title">选择校区</div>
        <button v-for="c in campusPicker.items" :key="c.id" class="campus-opt" @click="goCampus(c)">
          <span class="campus-name">{{ c.name }}</span>
        </button>
      </div>
    </Teleport>

    <!-- 竞赛获奖 -->
    <div v-if="awardData || chuangkeData || scienceLiteracyData || techSportsData || scienceExperimentData || yueyunbeiData" class="card">
      <div class="card-title">竞赛获奖</div>
      <div v-if="awardData" class="award-block">
        <RouterLink :to="{ path: '/awards', query: { competition: 'innovation', stage, school: schoolId } }" class="award-name">广州市中小学生创新大赛 ›</RouterLink>
        <p class="sub-note">{{ stageLabel }}组（{{ innovationYearsLabel }}）</p>
        <div v-for="yr in awardYears" :key="yr" class="award-year">
          <span class="award-year-label">{{ yr }}</span>
          <span v-if="awardData[yr] && awardData[yr].gold" class="medal gold">{{ awardData[yr].gold}}金</span>
          <span v-if="awardData[yr] && awardData[yr].silver" class="medal silver">{{ awardData[yr].silver}}银</span>
          <span v-if="awardData[yr] && awardData[yr].bronze" class="medal bronze">{{ awardData[yr].bronze}}铜</span>
        </div>
      </div>
      <div v-if="chuangkeData" class="award-block" style="margin-top:12px">
        <RouterLink :to="{ path: '/awards', query: { competition: 'chuangke', stage, school: schoolId } }" class="award-name">广州市中小学生科技创客电视大赛 ›</RouterLink>
        <p class="sub-note">{{ chuangkeGroupLabel }}（{{ chuangkeYearsLabel }}）</p>
        <div v-for="yr in Object.keys(chuangkeData).sort().reverse()" :key="yr" class="award-year">
          <span class="award-year-label">{{ yr }}</span>
          <span v-if="chuangkeData[yr]?.gold" class="medal gold">{{ chuangkeData[yr]?.gold }}个一等奖</span>
          <span v-if="chuangkeData[yr]?.silver" class="medal silver">{{ chuangkeData[yr]?.silver }}个二等奖</span>
          <span v-if="chuangkeData[yr]?.bronze" class="medal bronze">{{ chuangkeData[yr]?.bronze }}个三等奖</span>
        </div>
      </div>
      <div v-if="scienceLiteracyData" class="award-block" style="margin-top:12px">
        <RouterLink :to="{ path: '/awards', query: { competition: 'science_literacy', stage, school: schoolId } }" class="award-name">广州市中小学生科学素养大赛 ›</RouterLink>
        <p class="sub-note">{{ stageLabel }}组（{{ scienceLiteracyYearsLabel }}）</p>
        <div v-for="yr in Object.keys(scienceLiteracyData).sort().reverse()" :key="yr" class="award-year">
          <span class="award-year-label">{{ yr }}</span>
          <span v-if="scienceLiteracyData[yr]?.gold" class="medal gold">{{ scienceLiteracyData[yr]?.gold }}个一等奖</span>
          <span v-if="scienceLiteracyData[yr]?.silver" class="medal silver">{{ scienceLiteracyData[yr]?.silver }}个二等奖</span>
          <span v-if="scienceLiteracyData[yr]?.bronze" class="medal bronze">{{ scienceLiteracyData[yr]?.bronze }}个三等奖</span>
        </div>
      </div>
      <div v-if="techSportsData" class="award-block" style="margin-top:12px">
        <RouterLink :to="{ path: '/awards', query: { competition: 'tech_sports', stage, school: schoolId } }" class="award-name">广州市中小学生科技体育教育竞赛 ›</RouterLink>
        <p class="sub-note">{{ stage === 'high' ? '中学组 + 测向18岁组' : techSportsStage === 'secondary' ? '中学组（初中+高中）' : stageLabel + '组' }}（{{ techSportsYearsLabel }}）</p>
        <div v-for="yr in Object.keys(techSportsData).sort().reverse()" :key="yr" class="award-year">
          <span class="award-year-label">{{ yr }}</span>
          <span v-if="techSportsData[yr]?.gold" class="medal gold">{{ techSportsData[yr]?.gold }}个一等奖</span>
          <span v-if="techSportsData[yr]?.silver" class="medal silver">{{ techSportsData[yr]?.silver }}个二等奖</span>
          <span v-if="techSportsData[yr]?.bronze" class="medal bronze">{{ techSportsData[yr]?.bronze }}个三等奖</span>
        </div>
      </div>
      <div v-if="scienceExperimentData" class="award-block" style="margin-top:12px">
        <RouterLink :to="{ path: '/awards', query: { competition: 'science_experiment', stage, school: schoolId } }" class="award-name">广州市中小学科学实验大赛 ›</RouterLink>
        <p class="sub-note">{{ stageLabel }}组（{{ scienceExperimentYearsLabel }}）</p>
        <div v-for="yr in Object.keys(scienceExperimentData).sort().reverse()" :key="yr" class="award-year">
          <span class="award-year-label">{{ yr }}</span>
          <span v-if="scienceExperimentData[yr]?.gold" class="medal gold">{{ scienceExperimentData[yr]?.gold }}个一等奖</span>
          <span v-if="scienceExperimentData[yr]?.silver" class="medal silver">{{ scienceExperimentData[yr]?.silver }}个二等奖</span>
          <span v-if="scienceExperimentData[yr]?.bronze" class="medal bronze">{{ scienceExperimentData[yr]?.bronze }}个三等奖</span>
        </div>
      </div>
      <div v-if="yueyunbeiData" class="award-block" style="margin-top:12px">
        <RouterLink :to="{ path: '/awards', query: { competition: 'yueyunbei', stage, school: schoolId } }" class="award-name">粤韵杯湾区中小学生文学与艺术素养大赛 ›</RouterLink>
        <p class="sub-note">{{ stageLabel }}组（{{ yueyunbeiYearsLabel }}）</p>
        <div v-for="yr in Object.keys(yueyunbeiData).sort().reverse()" :key="yr" class="award-year">
          <span class="award-year-label">{{ yr }}</span>
          <span v-if="yueyunbeiData[yr]?.gold" class="medal gold">{{ yueyunbeiData[yr]?.gold }}个一等奖</span>
          <span v-if="yueyunbeiData[yr]?.silver" class="medal silver">{{ yueyunbeiData[yr]?.silver }}个二等奖</span>
          <span v-if="yueyunbeiData[yr]?.bronze" class="medal bronze">{{ yueyunbeiData[yr]?.bronze }}个三等奖</span>
        </div>
      </div>
    </div>

    <!-- 初中 tab：升学通道（名额分配/自招，LinkagePanel） -->
    <template v-if="stage === 'middle'">
      <LinkagePanel :stage="'middle'" :school="schoolName" />
    </template>

    <!-- 高中 tab：高考信息在上，招生计划（中考线+名额覆盖）在下 -->
    <template v-if="stage === 'high'">
      <div class="card" v-if="gaokaoRows.length">
        <div class="card-title">高考信息</div>
        <div class="kv">
          <div class="kv-row" v-for="r in gaokaoRows" :key="r.label">
            <span>{{ r.label }}</span><b>{{ r.value }}</b>
          </div>
        </div>
        <p class="sub-note">高分段/特控率为各校喜报或网传，非官方统一发布，仅供参考。</p>
      </div>
      <div class="card" v-if="admissionRows.length">
        <div class="card-title">招生计划</div>
        <div class="kv">
          <div class="kv-row" v-for="r in admissionRows" :key="r.label">
            <span>{{ r.label }}</span><b :class="{ strong: r.strong }">{{ r.value }}</b>
          </div>
        </div>
        <p class="sub-note">录取线为官方发布：公办为户籍生最低分，民办为最低分（含公费班），外语艺术类为末位考生分数；2025/2026 两年同屏展示。</p>
      </div>
      <LinkagePanel :stage="'high'" :school="schoolName" :school-id="schoolId" />
    </template>

    <!-- 品牌关联 + 校区（合并） -->
    <div v-if="brandCardUseful || multiCampusCardUseful" class="card">
      <div class="card-title">品牌关联</div>
      <template v-if="brandCard">
        <p class="sub-note">同一品牌下的校区与学校，按法人关系分组。</p>
        <div class="brand-head">品牌 · {{ brandCard.brand }}</div>
        <p v-if="brandCard.note" class="brand-note">
          {{ brandCard.note }}
          <span v-if="brandCard.sourceUrls?.length" class="brand-sources">
            <a
              v-for="(url, i) in brandCard.sourceUrls"
              :key="i"
              :href="url"
              target="_blank"
              rel="noopener noreferrer"
              class="brand-source-link"
            >[官方文件{{ brandCard.sourceUrls.length > 1 ? ' ' + (i + 1) : '' }}]</a>
          </span>
        </p>
        <div v-for="g in brandCard.groups" :key="g.key" class="brand-group">
          <div class="brand-group-title" :class="g.key">{{ g.title }}</div>
          <div v-for="r in g.rows" :key="r.name" class="brand-row" :class="{ current: r.isCurrent }">
            <div class="brand-row-main">
              <RouterLink v-if="r.link && !r.isCurrent" :to="r.link" class="brand-name-link">{{ r.name }}</RouterLink>
              <span v-else class="brand-name-link">{{ r.name }}</span>
              <span v-if="r.isCurrent" class="tag tag-now">当前查看</span>
              <span v-if="r.role === '核心校'" class="tag">核心校</span>
              <span v-if="r.relationType" class="tag">{{ { entrusted: '托管办学', cooperation: '合作办学', brand: '品牌合作' }[r.relationType] }}</span>
              <span v-else-if="r.role !== '核心校'" class="tag">成员校</span>
            </div>
            <div class="brand-row-badges">
              <span v-if="r.district" class="badge b-district">{{ r.district }}</span>
              <span v-for="s in r.stages" :key="s" class="badge b-stage">{{ s }}</span>
              <span v-if="r.badge" class="badge" :class="r.badge.cls">{{ r.badge.text }}</span>
            </div>
            <p v-if="r.reason" class="brand-reason">{{ r.reason }}</p>
          </div>
        </div>
      </template>
      <template v-else-if="multiCampusCard">
        <p class="sub-note">该校未收录为教育集团成员；以下校区由实体注册表按同一法人推导。</p>
        <div v-for="g in multiCampusCard.groups" :key="g.key" class="brand-group">
          <div class="brand-group-title" :class="g.key">{{ g.title }}</div>
          <div v-for="r in g.rows" :key="r.name" class="brand-row" :class="{ current: r.isCurrent }">
            <div class="brand-row-main">
              <RouterLink v-if="r.link && !r.isCurrent" :to="r.link" class="brand-name-link">{{ r.name }}</RouterLink>
              <span v-else class="brand-name-link">{{ r.name }}</span>
              <span v-if="r.isCurrent" class="tag tag-now">当前查看</span>
              <span class="tag">{{ r.role }}</span>
            </div>
            <div class="brand-row-badges">
              <span v-if="r.district" class="badge b-district">{{ r.district }}</span>
              <span v-for="s in r.stages" :key="s" class="badge b-stage">{{ s }}</span>
            </div>
          </div>
        </div>
      </template>
      <!-- 无品牌集团卡片时，校区列表用 brand-row 风格（可点击 + 学部 badge） -->
      <div v-if="!brandCardUseful && campuses && campuses.length > 1" class="brand-group">
        <div v-for="c in campuses" :key="c" class="brand-row">
          <div class="brand-row-main">
            <RouterLink v-if="repository.resolvePoiName(c)" :to="`/school/${encodeURIComponent(repository.resolvePoiName(c)!)}?stage=high`" class="brand-name-link">{{ c }}</RouterLink>
            <template v-else>{{ c }}</template>
            <span class="tag">校区</span>
          </div>
        </div>
      </div>
    </div>

    <footer class="d-foot">
      <button class="back" @click="goBack">← 返回</button>
    <button class="back" style="margin-left:12px;" @click="viewOnMap">在地图中查看</button>
      <RouterLink v-if="stage === 'middle'" to="/linkage" class="back">升学路径总览 →</RouterLink>
    </footer>
  </section>
</template>

<style scoped>
.detail { max-width: 720px; margin: 0 auto; }
.back { display: inline-block; color: #1a6bd6; text-decoration: none; font-size: 13px; margin-bottom: 10px; background: none; border: none; cursor: pointer; font-family: inherit; padding: 0; }
.back:hover { text-decoration: underline; }
.award-year { display: flex; align-items: center; gap: 8px; padding: 6px 0; }
.award-name { font-size:14px; font-weight:600; color:#2563eb; text-decoration:none; }
.award-year-label { font-size: 13px; font-weight: 600; color: #374151; min-width: 40px; }
.medal { font-size: 12px; font-weight: 700; color: #fff; border-radius: 4px; padding: 2px 8px; }
.medal.gold { background: #d4a017; }
.medal.silver { background: #6b7280; }
.medal.bronze { background: #b45309; }
.d-head { margin-bottom: 14px; }
.stage-tabs { display: flex; gap: 8px; margin: 0 0 14px; }
.stage-tab { padding: 6px 16px; border: 1px solid #d9d9d9; border-radius: 999px; background: #fff; cursor: pointer; font-size: 14px; }
.stage-tab.on { background: #1a73e8; color: #fff; border-color: #1a73e8; }
.d-head h1 { font-size: 20px; font-weight: 700; margin: 0 0 8px; line-height: 1.4; }
.badges { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.badge { font-size: 12px; font-weight: 700; color: #fff; border-radius: 6px; padding: 2px 9px; }
.stage { font-size: 12px; color: #6b7280; }

.badge.sm { font-size: 10.5px; padding: 1px 7px; vertical-align: middle; margin-left: 6px; }
.title-note-row { margin: -4px 0 10px; display: flex; align-items: center; gap: 6px; }
.title-note { font-size: 11px; color: #9aa0a6; font-weight: 400; }

.badge.b-district { background: #e5e7eb; color: #374151; }
.badge.b-stage { background: #dbeafe; color: #1e40af; }
.badge.b-license { background: #4b5563; }
.badge.b-hcity { background: #b45309; }
.badge.b-national { background: #9f1239; }
.badge.b-province { background: #1d4ed8; }
.badge.b-city { background: #047857; }
.badge.b-hdist { background: #0f766e; }
.badge.b-minban { background: #9333ea; }
.badge.b-full { background: #e11d48; }
.badge.b-part { background: #f59e0b; }
.badge.b-none { background: #8a94a6; }

.d-sub { font-size: 12.5px; color: #6b7280; margin: 8px 0 0; line-height: 1.6; }
.not-included-card { margin: 10px 0 0; padding: 8px 12px; border-radius: 8px; background: #fff7e6; border: 1px solid #ffe1a8; font-size: 12px; color: #9a6700; line-height: 1.6; }

.badge.license { background: #4b5563; }
.badge.h-city { background: #b45309; }
.badge.h-dist { background: #0f766e; }
.badge.h-normal { background: #57534e; }

/* 初中招生机制徽章 */
.badge.single_zone { background: #0f766e; }
.badge.zhi_sheng { background: #047857; }
.badge.group_paidui { background: #1e40af; }
.badge.single_paidui { background: #dc2626; }
.badge.min_zi_zhu { background: #7c3aed; }
.badge.no_plan { background: #6b7280; }
.plan-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.plan-total { font-size: 13px; font-weight: 700; color: #1a1b1c; font-variant-numeric: tabular-nums; }
.mech-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.mech-head { display: inline-flex; align-items: center; gap: 10px; }
.sub-block { margin-top: 10px; }
.sub-title { font-size: 12.5px; font-weight: 700; color: #1e40af; margin-bottom: 4px; }
.school-link { color: #1a6bd6; text-decoration: underline; text-underline-offset: 2px; }
.campus-open { font: inherit; background: none; border: 0; padding: 0; cursor: pointer; text-align: left; }
.campus-open:hover { color: #0e4fb0; }
.campus-mask { position: fixed; inset: 0; z-index: 1350; background: rgba(0, 0, 0, 0.03); }
.campus-pop {
  position: fixed; z-index: 1400; width: 300px; max-width: 86vw;
  background: #fff; border: 1px solid #e4e3dd; border-radius: 12px;
  box-shadow: 0 10px 30px rgba(20, 30, 50, 0.16); padding: 8px;
}
.campus-pop-title { font-size: 12.5px; font-weight: 700; color: #1a1b1c; padding: 4px 6px 8px; }
.campus-opt {
  display: flex; align-items: center; gap: 8px; width: 100%; border: 0;
  background: transparent; border-radius: 8px; padding: 7px 8px;
  font-size: 12.5px; color: #1a6bd6; cursor: pointer; text-align: left;
}
.campus-opt:hover { background: #f2f7ff; }
.campus-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lottery-warning {
  margin-top: 10px; padding: 8px 10px; border-radius: 8px;
  background: #fef2f2; border: 1px solid #fecaca;
  color: #991b1b; font-size: 12px; line-height: 1.6;
}

.card {
  background: #fff; border: 1px solid #e4e3dd; border-radius: 14px;
  padding: 14px 16px; margin-bottom: 12px;
}
.card-title { font-size: 13px; font-weight: 700; color: #1a1b1c; margin-bottom: 10px; }
.sub-note { font-size: 11px; color: #9aa0a6; line-height: 1.6; margin: 0 0 10px; }
.empty { font-size: 12.5px; color: #9aa0a6; margin: 4px 0; line-height: 1.6; }
.note-text { font-size: 12.5px; color: #444; margin: 0; line-height: 1.7; }

.kv { display: flex; flex-direction: column; gap: 6px; }
.kv-row { display: flex; gap: 10px; font-size: 12.5px; align-items: baseline; }
.kv-row > span { flex: none; width: 100px; color: #6b7280; font-size: 11.5px; }
.kv-row > b { font-weight: 600; line-height: 1.6; }
.kv-row > b.strong { color: #1a1b1c; }

/* 学校特色：多行称号列表，label 顶对齐 */
.specialty-row { align-items: flex-start; }
.specialty-row > span { padding-top: 2px; }
.specialty-line { line-height: 1.7; }
.specialty-link { color: inherit; text-decoration: none; }
.specialty-link:hover { text-decoration: underline; }

.zone-block { margin-top: 10px; }
.zone-label { font-size: 11px; color: #6b7280; font-weight: 600; margin-bottom: 4px; }
.zone-block p {
  margin: 0; background: #f7f6f2; border-radius: 8px; padding: 8px 10px;
  font-size: 12px; color: #444; line-height: 1.7;
  white-space: pre-line; /* zone 树结构含 \n 换行，保留层级缩进 */
}

.feed-list { display: flex; flex-direction: column; gap: 6px; }
.feed-item { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12.5px; }
.feed-name { color: #1a6bd6; text-decoration: none; font-weight: 500; }
.feed-name:hover { text-decoration: underline; }
.tag { font-size: 11px; color: #6b7280; background: #f1f0ec; border-radius: 5px; padding: 2px 8px; font-variant-numeric: tabular-nums; }
.tag-dim { color: #9aa0a6; }

.bars { display: flex; flex-direction: column; gap: 5px; margin-top: 10px; }
.bar-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.bar-name { flex: none; width: 76px; color: #6b7280; font-size: 11.5px; }
.bar-track { flex: 1; height: 12px; background: #f1f0ec; border-radius: 6px; overflow: hidden; }
.bar-fill { display: block; height: 100%; background: #9bbbf4; border-radius: 6px; }
.bar-val { flex: none; width: 26px; text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }

.tbl { display: flex; flex-direction: column; gap: 4px; }
.tbl-row { display: flex; align-items: center; gap: 8px; font-size: 12px; padding: 4px 6px; border-radius: 6px; }
.tbl-row > span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tbl-row > span:nth-child(n+2) { flex: none; width: 52px; text-align: right; font-variant-numeric: tabular-nums; }
.tbl-row .strong { color: #1a6bd6; font-weight: 700; }
.tbl-head { background: #f7f6f2; font-size: 11px; color: #6b7280; font-weight: 600; }
.tbl-head > span { color: #6b7280; }

.campus-list { margin: 0; padding-left: 18px; font-size: 12.5px; color: #444; line-height: 1.8; }
.d-foot { display: flex; justify-content: space-between; margin-top: 6px; }

/* 品牌关联板块 */
.brand-head { font-size: 12.5px; font-weight: 700; color: #1a1b1c; margin-bottom: 4px; }
.brand-note { font-size: 12px; color: #444; line-height: 1.7; margin: 0 0 10px; background: #f7f6f2; border-radius: 8px; padding: 8px 10px; }
.brand-sources { margin-left: 6px; }
.brand-source-link { color: #2563eb; text-decoration: none; margin-right: 4px; }
.brand-source-link:hover { text-decoration: underline; }
.brand-group { margin-bottom: 10px; }
.brand-group:last-child { margin-bottom: 0; }
.brand-group-title { font-size: 11.5px; font-weight: 700; color: #6b7280; margin-bottom: 6px; }
.brand-group-title.same { color: #1e40af; }
.brand-group-title.independent { color: #b45309; }
.brand-row { border: 1px solid #eee; border-radius: 10px; padding: 8px 10px; margin-bottom: 6px; }
.brand-row:last-child { margin-bottom: 0; }
.brand-row.current { border-color: #9bbbf4; background: rgba(155, 187, 244, 0.08); }
.brand-row-main { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; font-size: 12.5px; }
.brand-name-link { color: #1a6bd6; text-decoration: none; font-weight: 600; }
.brand-name-link:hover { text-decoration: underline; }
.brand-name-plain { font-weight: 600; }
.tag-now { background: #9bbbf4; color: #fff; }
.brand-row-badges { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 6px; }
.brand-reason { font-size: 11px; color: #6b7280; line-height: 1.6; margin: 6px 0 0; }

@media (max-width: 600px) {
  .kv-row > span { width: 84px; }
  .bar-name { width: 64px; }
}
</style>
