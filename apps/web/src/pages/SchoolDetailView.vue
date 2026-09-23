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
  buildDetailModel, buildAliasTable, matchTier1ByPoiName, normName,
  formatPrimarySignals, formatMiddleSignals, highScoreRows,
  type SchoolStage, type SchoolPoi, type Tier1School, type HighLevelSchool,
} from '@gz/shared';
import {
  repository, primarySchools, middleSchools, highSchools, primaryTier1, middleTier1,
  highLevels, tier1Schools, middleTier1Schools, entities, matchEnrollment,
  middleQuotaSummary, middleEnrollmentsOf, middleEnrollmentGroups, xiaoshengchuOf, schoolBadges, scoresOfSchool,
  isComprehensive, groupOfSchool, resolvePoiName, resolveSchoolIdOf,
  type BrandUnit,
  innovationAwards,
  chuangkeAwards,
  scienceLiteracyAwards,
  detailedRecords,
  specialtySchools,
} from '../data';
import LinkagePanel from '../components/LinkagePanel.vue';

/** note 中「(见)说明N」拆成可点击片段：跳转番禺区 2026 年小学招生政策说明页 explain-N 锚点。
 *  仅命中「见?说明\d+」，其余文本（如白云/天河普通备注）原样输出，不误伤。 */
type NoteSeg = { text?: string; raw?: string; explain?: number };
const noteSegments = (note: string): NoteSeg[] => {
  const re = /见?说明(\d+)/g;
  const segs: NoteSeg[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(note))) {
    if (m.index > last) segs.push({ text: note.slice(last, m.index) });
    segs.push({ raw: m[0], explain: Number(m[1]) });
    last = m.index + m[0].length;
  }
  if (last < note.length) segs.push({ text: note.slice(last) });
  return segs.length ? segs : [{ text: note }];
};
/** 招生说明片段（「见说明N」→ 可点击，其余文本原样） */
const noteSegs = computed<NoteSeg[]>(() => (enrollment.value?.note ? noteSegments(enrollment.value.note) : []));
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
const feedJuniors = computed(() => model.value.feedJuniors);
const feedGap = computed(() => model.value.feedGap);
const feedRows = computed(() => model.value.feedRows);
const enrollNote = computed(() => model.value.enrollNote);
const signalRows = computed(() => model.value.signalRows);
const admissionRows = computed(() => model.value.admissionRows);
const gaokaoRows = computed(() => model.value.gaokaoRows);
const brandCard = computed(() => model.value.brandCard);
const brandCardUseful = computed(() => model.value.brandCardUseful);
const campuses = computed(() => model.value.campuses);
/** 创新大赛获奖：按当前 school_id 查，有则展示金/银/铜（分学段分年份） */
const awardData = computed(() => innovationAwards[schoolId.value]?.innovation_awards?.stages?.[stage.value]);
/** 创客电视大赛官方只有小学组/中学组，中学组同时覆盖初中和高中。 */
const chuangkeStage = computed(() => stage.value === 'middle' || stage.value === 'high' ? 'secondary' : stage.value);
const chuangkeData = computed(() => chuangkeAwards[schoolId.value]?.chuangke_awards?.stages?.[chuangkeStage.value]);
const chuangkeGroupLabel = computed(() => chuangkeStage.value === 'secondary' ? '中学组（初中+高中）' : stageLabel.value);
const scienceLiteracyData = computed(() => scienceLiteracyAwards[schoolId.value]?.science_literacy_awards?.stages?.[stage.value]);
const awardYears = computed(() => awardData.value ? Object.keys(awardData.value).sort().reverse() : []);
const awardRecords = detailedRecords as Array<{ competition?: string; year?: number }>;
function competitionYearsLabel(competition: string) {
  const years = [...new Set(awardRecords.filter((record) => record.competition === competition && Number.isFinite(record.year)).map((record) => record.year as number))].sort((a, b) => a - b);
  return years.length > 1 ? `${years[0]}-${years[years.length - 1]}` : (years[0] || '');
}
const innovationYearsLabel = computed(() => competitionYearsLabel('innovation'));
const chuangkeYearsLabel = computed(() => competitionYearsLabel('chuangke'));
const scienceLiteracyYearsLabel = computed(() => competitionYearsLabel('science_literacy'));
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
/** 派位组生源小学（groups[gid].primaries，组级对口）；无则空列表 */
function groupPrimariesOf(gid?: string | null): string[] {
  return gid ? (middleEnrollmentGroups[gid]?.primaries ?? []) : [];
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

    <!-- 学校信号（历史称号/集团/喜报/录取线等源数据，民间口径非官方评价） -->
    <div v-if="signalRows.length" class="card">
      <div class="card-title">学校信号</div>
      <div class="title-note-row">
        <span class="title-note">民间口径，非官方评价，仅供参考。</span>
      </div>
      <div class="kv">
        <div class="kv-row" v-for="r in signalRows" :key="r.label">
          <span>{{ r.label }}</span><b>{{ r.value }}</b>
        </div>
      </div>
    </div>

    <!-- 小学 tab：招生计划 + 所在区小升初机制 -->
    <div v-if="stage === 'primary'" class="card">
      <div class="card-title">招生计划（2026）</div>
      <div v-if="enrollment" class="kv">
        <div class="kv-row"><span>计划班数</span><b>{{ enrollment.plan_classes ?? '—' }} 个班</b></div>
        <div class="kv-row" v-if="enrollment.plan_count"><span>计划人数</span><b>{{ enrollment.plan_count }} 人</b></div>
        <div class="kv-row" v-if="enrollment.nature"><span>办学性质</span><b>{{ enrollment.nature }}</b></div>
        <div class="kv-row" v-if="enrollment.source"><span>数据来源</span><b>{{ enrollment.source }}</b></div>
        <div v-if="enrollment.zone" class="zone-block">
          <div class="zone-label">招生地段（对口）</div>
          <p>{{ enrollment.zone }}</p>
        </div>
        <div v-if="enrollment.note" class="zone-block">
          <div class="zone-label">招生说明</div>
          <p v-for="(seg, i) in noteSegs" :key="i"><RouterLink v-if="seg.explain" :to="{ path: '/policy', query: { explain: seg.explain } }" class="note-link">{{ seg.raw }}</RouterLink><template v-else>{{ seg.text }}</template></p>
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

    <!-- 初中 tab：招生计划（2026）：班数/范围/机制 + 生源小学 -->
    <div v-if="stage === 'middle'" class="card">
      <div class="card-title">招生计划（2026）</div>
      <p v-if="enrollNote" class="sub-note">{{ enrollNote }}</p>

      <!-- 机制徽章 + 班数 + 范围（来自初中招生计划表）；一校多规则时逐条渲染 -->
      <template v-if="middleEnrolls.length">
        <div v-for="(m, mi) in middleEnrolls" :key="`${m.district}-${m.record.school}`" class="mech-block" :style="mi ? 'border-top:1px dashed #e5e7eb;margin-top:10px;padding-top:10px;' : ''">
          <div class="mech-row">
            <span v-if="middleEnrolls.length > 1" class="badge b-district">{{ m.district }}</span>
            <span class="badge" :class="m.record.mechanism">
              {{ m.mechanismDef.label }}
            </span>
            <span v-if="m.record.plan_classes != null" class="mech-plan">
              计划 {{ m.record.plan_classes }} 个班
            </span>
          </div>
          <div v-if="m.record.scope" class="zone-block">
            <div class="zone-label">招生服务范围</div>
            <p>{{ m.record.scope }}</p>
          </div>
          <p v-if="m.record.mechanism_note" class="sub-note">
            官方备注：{{ m.record.mechanism_note }}
          </p>
          <!-- 生源小学：本组对口派位小学（组级，与「派位组成员」同组） -->
          <div v-if="groupPrimariesOf(m.record.group_id).length" class="zone-block">
            <div class="zone-label">生源小学（本组对口派位）</div>
            <div class="feed-list">
              <div v-for="p in groupPrimariesOf(m.record.group_id)" :key="p" class="feed-item">
                <span class="feed-name">{{ p }}</span>
              </div>
            </div>
          </div>
          <!-- 派位组：多校派位时列出组内学校（每行一所，点击跳转该校详情） -->
          <div v-if="m.record.group_members && m.record.group_members.length" class="zone-block">
            <div class="zone-label">派位组成员（随机分配，组内兜底）</div>
            <div class="feed-list">
              <div v-for="gm in m.record.group_members" :key="gm" class="feed-item">
                <RouterLink :to="`/school/${encodeURIComponent(resolvePoiName(gm) || gm)}?stage=middle`" class="feed-name">{{ gm }}</RouterLink>
                <span class="tag tag-dim">{{ groupNameOf(m.record.group_id) }}</span>
              </div>
            </div>
          </div>
          <!-- 单校电脑抽签：红字警示 -->
          <div v-if="m.mechanismDef.can_lose && m.mechanismDef.lose_text" class="lottery-warning">
            ⚠️ {{ m.mechanismDef.lose_text }}
          </div>
        </div>
      </template>

      <p v-if="!middleEnrolls.length" class="empty">暂无招生计划数据：2026 公办初中招生计划表未收录本校，以区教育局当年正式文件为准。</p>
    </div>

    <!-- 竞赛获奖 -->
    <div v-if="awardData || chuangkeData || scienceLiteracyData" class="card">
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
    <div v-if="brandCardUseful" class="card">
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
              <RouterLink v-if="r.link" :to="r.link" class="brand-name-link">{{ r.name }}</RouterLink>
              <span v-else class="brand-name-plain">{{ r.name }}</span>
              <span v-if="r.isCurrent" class="tag tag-now">当前查看</span>
              <span class="tag">{{ r.role }}</span>
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
.badge.b-tier { background: #e11d48; }
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

.badge.tier-full { background: #e11d48; }
.badge.tier-part { background: #f59e0b; }
.badge.tier-none { background: #8a94a6; }
.badge.license { background: #4b5563; }
.badge.h-city { background: #b45309; }
.badge.h-dist { background: #0f766e; }
.badge.h-normal { background: #57534e; }

/* 初中招生机制徽章 */
.badge.single_zone { background: #0f766e; }
.badge.group_paidui { background: #1e40af; }
.badge.single_lottery { background: #dc2626; }
.mech-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.mech-plan { font-size: 13px; font-weight: 600; color: #1a1b1c; }
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
.note-link { color: #1a73e8; text-decoration: none; border-bottom: 1px dashed #1a73e8; cursor: pointer; }
.note-link:hover { color: #1765cc; }
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
