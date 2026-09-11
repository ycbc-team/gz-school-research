<script setup lang="ts">
/**
 * 升学路径面板（公共组件）：
 * - stage='middle'：指定初中的四通道升学数据（名额分配 21 校区 / 自招·体育·艺术 / 第二批次录取分数）
 * - stage='high'：指定高中的名额分配覆盖初中 + 特殊通道覆盖（按学校聚合全部校区）
 * 数据组装已下沉 @gz/shared buildLinkageModel（与小程序详情页共用），本组件只做渲染。
 */
import { computed } from 'vue';
import { buildLinkageModel } from '@gz/shared';
import { repository } from '../data';

const props = defineProps<{ stage: 'middle' | 'high'; school: string }>();
const schoolName = computed(() => decodeURIComponent(props.school || ''));
const model = computed(() => buildLinkageModel(props.stage, schoolName.value, repository));
</script>

<template>
  <!-- ===== 初中视角：按录取批次组织 ===== -->
  <template v-if="stage === 'middle'">
    <div class="card" v-if="model.specialRows.length">
      <div class="card-title">中考-第一批</div>
      <p class="sub-note">特殊通道：自主招生 / 体育 / 艺术特长生。本校学生通过特殊通道被以下高中录取（资格名单人数，非最终预录取）。</p>
      <div class="tbl">
        <div class="tbl-row tbl-head"><span>升入高中</span><span>自招</span><span>体育</span><span>艺术</span><span>合计</span></div>
        <div v-for="r in model.specialRows" :key="r.campus" class="tbl-row">
          <span><RouterLink :to="`/school/${encodeURIComponent(r.school)}?stage=high`" class="sch-link">{{ r.campusFull || r.campus }}</RouterLink></span><span>{{ r.autonomy }}</span><span>{{ r.sports }}</span><span>{{ r.arts }}</span><span class="strong">{{ r.autonomy + r.sports + r.arts }}</span>
        </div>
      </div>
    </div>

    <div class="card" v-if="model.quota && (model.batchMerged.length || model.quota.qu_quota != null)">
      <div class="card-title">中考-第二批</div>
      <p class="sub-note">名额分配（指标到校）：本校名额考生按政策获得以下高中的名额。按高中隶属分省市属、区属两块。</p>
      <div class="kv">
        <div class="kv-row"><span>名额考生数</span><b>{{ model.quota.kaosheng ?? '—' }} 人</b></div>
        <div class="kv-row"><span>省市属名额合计</span><b>{{ model.quota.sheng_quota ?? '—' }} 个</b></div>
        <div class="kv-row"><span>区属名额合计</span><b>{{ model.quota.qu_quota ?? '—' }} 个</b></div>
      </div>

      <div v-if="model.batchMerged.length" class="qblock">
        <div class="qblock-title">省市属高中（面向全市）</div>
        <div class="tbl tbl-merged" style="margin-top:6px;">
          <div class="tbl-row tbl-head"><span>高中</span><span>名额</span><span>录取最低分</span></div>
          <div v-for="r in model.batchMerged" :key="r.campus" class="tbl-row">
            <span><RouterLink :to="`/school/${encodeURIComponent(r.school)}?stage=high`" class="sch-link">{{ r.campusFull || r.campus }}</RouterLink></span><span>{{ r.n ?? '—' }}</span><span>{{ r.min ?? '—' }}</span>
          </div>
        </div>
      </div>

      <div v-if="model.districtRows.length" class="qblock">
        <div class="qblock-title">区属高中（面向本区）</div>
        <p class="sub-note" style="margin-top:4px;color:#999;font-size:12px;">数据从官方 PDF 视觉提取，个别个位数可能存在 1~6 个误差，具体名额以官方公布为准。</p>
        <div class="tbl tbl-merged" style="margin-top:6px;">
          <div class="tbl-row tbl-head"><span>高中</span><span>名额</span></div>
          <div v-for="r in model.districtRows" :key="r.name" class="tbl-row">
            <span><RouterLink :to="`/school/${encodeURIComponent(r.name)}?stage=high`" class="sch-link">{{ r.name }}</RouterLink></span><span class="strong">{{ r.n }}</span>
          </div>
        </div>
      </div>
      <div v-else-if="model.quota.qu_quota != null" class="qblock">
        <div class="qblock-title">区属高中（面向本区）</div>
        <p class="sub-note" style="margin-top:6px;">区属名额分配到本区区属高中，共 {{ model.quota.qu_quota }} 个。逐校明细未收录。</p>
      </div>

      <p class="sub-note" style="margin-top:8px;">第三批（省市属统招）、第四批（区属统招）按全市统一投档划线，官方不公布按初中学校的录取名单与分数，故不展示。</p>
    </div>

    <div class="card" v-if="!model.hasMiddleData">
      <div class="card-title">升学通道</div>
      <p class="empty">该初中暂未匹配到省市属高中升学通道数据（可能为未收录或非名额分配学校）。</p>
    </div>
  </template>

  <!-- ===== 高中视角：覆盖反查（第一批特殊通道 → 第二批次额分配） ===== -->
  <template v-else>
    <div class="card" v-if="model.highSpecialCoverage.length">
      <div class="card-title">第一批招生（2026）</div>
      <p class="sub-note">特殊通道（自主招生 / 体育 / 艺术特长生）覆盖初中，按合计人数降序。</p>
      <div class="tbl">
        <div class="tbl-row tbl-head"><span>初中</span><span>自招</span><span>体育</span><span>艺术</span></div>
        <div v-for="r in model.highSpecialCoverage" :key="r.school" class="tbl-row">
          <span>{{ r.school }}</span><span>{{ r.autonomy }}</span><span>{{ r.sports }}</span><span>{{ r.arts }}</span>
        </div>
      </div>
    </div>

    <div class="card" v-if="model.highCoverage.length || model.highDistrictCoverage.length">
      <div class="card-title">第二批招生（2026）</div>
      <div v-if="model.highCoverage.length" class="qblock">
        <div class="qblock-title">省市属高中（面向全市）覆盖初中</div>
        <div class="tbl" style="margin-top:6px;">
          <div class="tbl-row tbl-head"><span>初中</span><span>所在区</span><span>名额</span></div>
          <div v-for="r in model.highCoverage" :key="r.school" class="tbl-row">
            <span><RouterLink :to="`/school/${encodeURIComponent(r.school)}?stage=middle`" class="sch-link">{{ r.school }}</RouterLink></span>
            <span>{{ r.districts.join('、') || '—' }}</span><span class="strong">{{ r.n }}</span>
          </div>
        </div>
      </div>
      <div v-if="model.highDistrictCoverage.length" class="qblock">
        <div class="qblock-title">区属高中（面向本区）覆盖初中</div>
        <div class="tbl" style="margin-top:6px;">
          <div class="tbl-row tbl-head"><span>初中</span><span>名额</span></div>
          <div v-for="r in model.highDistrictCoverage" :key="r.school" class="tbl-row">
            <span><RouterLink :to="`/school/${encodeURIComponent(r.school)}?stage=middle`" class="sch-link">{{ r.school }}</RouterLink></span>
            <span class="strong">{{ r.n }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card" v-if="!model.highCoverage.length && !model.highSpecialCoverage.length && !model.highDistrictCoverage.length">
      <div class="card-title">升学通道</div>
      <p class="empty">该校为区属高中：名额分配面向本区初中、官方未公布逐初中明细；省市属自招/特长等特殊通道暂未覆盖到本校。</p>
    </div>
  </template>
</template>

<style scoped>
.card {
  background: #fff; border: 1px solid #e4e3dd; border-radius: 14px;
  padding: 14px 16px; margin-bottom: 12px;
}
.card-title { font-size: 13px; font-weight: 700; color: #1a1b1c; margin-bottom: 10px; }
.qblock { margin-top: 12px; padding-top: 10px; border-top: 1px dashed #e4e3dd; }
.qblock:first-of-type { margin-top: 4px; }
.qblock-title { font-size: 12px; font-weight: 700; color: #374151; margin-bottom: 6px; }
.sub-note { font-size: 11px; color: #9aa0a6; line-height: 1.6; margin: 0 0 10px; }
.empty { font-size: 12.5px; color: #9aa0a6; margin: 4px 0; line-height: 1.6; }

.kv { display: flex; flex-direction: column; gap: 6px; }
.kv-row { display: flex; gap: 10px; font-size: 12.5px; align-items: baseline; }
.kv-row > span { flex: none; width: 100px; color: #6b7280; font-size: 11.5px; }
.kv-row > b { font-weight: 600; line-height: 1.6; }

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
.tbl-merged .tbl-row > span:nth-child(2) { width: 40px; }
.tbl-merged .tbl-row > span:nth-child(3) { width: 78px; }
.tbl-row .strong { color: #1a1b1c; font-weight: 700; }
.tbl-head { background: #f7f6f2; font-size: 11px; color: #6b7280; font-weight: 600; }
.tbl-head > span { color: #6b7280; }
.sch-link { color: #1a6bd6; text-decoration: none; }
.sch-link:hover { text-decoration: underline; }

@media (max-width: 600px) {
  .kv-row > span { width: 84px; }
  .bar-name { width: 64px; }
}
</style>
