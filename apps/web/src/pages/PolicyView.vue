<script setup lang="ts">
/**
 * 番禺区 2026 年小学招生政策说明
 * 内容整理自番禺区教育局《2026年番禺区义务教育阶段学校招生计划、招生地段及条件》
 * （原 apps/web/map/notes.html，旧版下线时随迁至新版，保持内容一致）
 */
const explains = [
  {
    id: 'explain-1',
    badge: '说明 1',
    title: '"人户一致"的认定条件',
    paras: [
      '"人户一致"条件适龄儿童需同时符合以下三个条件：',
      '一是适龄儿童在广州市公办小学招生入学规定时间内报名（一般5月上旬）。',
      '二是适龄儿童户籍地址与其父母或其他法定监护人所能提供的已收楼的房产证明地址一致，且父母或其他法定监护人拥有该房产100%份额，适龄儿童入户该址满1年以上（计算至入学当年的8月31日止）；或适龄儿童户籍地址所对应的已收楼的房产属于适龄儿童祖辈，且该祖辈拥有该房产100%份额，适龄儿童入户该址满3年以上（计算至入学当年的8月31日止）。',
      '三是适龄儿童申请入学的房产地址在入学当天（以9月1日为准）的前6年没有安排学生入读对口公办小学（同一父母或祖辈的适龄儿童除外）。',
      '考虑到"人户一致"政策的延续性及过渡性，以2021年8月31日为适龄儿童入户时间节点，按照"新人新办法，旧人旧办法"的原则执行，即2021年8月31日（含2021年8月31日当天）后入户的适龄儿童按上述"人户一致"条件执行。',
    ],
  },
  {
    id: 'explain-2',
    badge: '说明 2',
    title: '小区配建学校的学位安排',
    paras: [
      '凡小区内配建的义务教育公办学校，在解决该小区户籍（含符合广州市政策性照顾条件的业主子女）及附近居民符合"人户一致"条件的适龄儿童、少年入读，以及预留用作解决该年段将户籍迁到该住宅小区的适龄儿童、少年学位后，如有剩余学位，优先解决在小孩入学当年，该住宅小学近6年（或初中近3年）未有安排小孩入读该小区配建公办小学（或初中）的业主（指购房并在申请入学当年5月31日前收楼且拥有该房产100%份额。下同）子女。',
      '如果符合上述条件的小孩人数超出所剩余学位数，则按购房先后顺序安排；如果安排符合上述条件的小孩后还有剩余学位，所剩余的学位由各教育指导中心根据本学区实际情况统筹安排。',
      '详细招生细则见相关学校每年发布的招生方案。',
    ],
  },
  {
    id: 'explain-3',
    badge: '说明 3',
    title: '配建学校学位安排协议',
    paras: [
      '房地产开发商与其所在地镇政府（街道办事处）或教育行政部门签订了住宅小区配建学校学位安排协议的，原则上按协议的相关约定安排业主子女学位。详细招生细则见相关学校每年发布的招生方案。',
    ],
  },
  {
    id: 'explain-4',
    badge: '说明 4',
    title: '非"人户一致"与政策性照顾',
    paras: [
      '不符合"人户一致"入学条件的番禺区户籍适龄儿童，由户籍所在地教育指导中心统筹安排学位。政策性照顾学生由居住地所在教育指导中心统筹安排学位。',
    ],
  },
  {
    id: 'explain-5',
    badge: '说明 5',
    title: '地段调整与新增学校',
    paras: [
      '各公办小学招生服务地段以当年公布为准，若有新公办小学开办，则新开办学校区域内的公办小学招生服务地段有可能作相应的调整。',
    ],
  },
  {
    id: 'explain-6',
    badge: '说明 6',
    title: '预留学位',
    paras: [
      '各校招生人数中包含预留解决将户口迁至该招生范围且符合"人户一致"条件的适龄儿童学位，预留学位数由各教育指导中心根据实际情况而定。',
    ],
  },
  {
    id: 'explain-shiqiao',
    badge: '学区说明',
    title: '市桥城区学区特别说明',
    orange: true,
    paras: [
      '1. 由于市桥城区学区每年的适龄儿童数和分布都有变化，因此各校每年的招生地段可能有适当微调。',
      '2. 若房产权属是适龄儿童父母、在市桥城区学区内（含市桥街、桥南街、东环街、沙头街）迁移户籍的，地段生资格原则上不受入户年限限制（番禺中学附属学校除外），但须在番禺区教育局公布当年招生地段、计划前办妥有关户籍迁移手续，否则作为统筹生统筹安排入学。',
      '3. 市桥富豪山庄小学、市桥金山谷学校、市桥新世纪小学见说明2，蚬涌俊贤学校见说明3。',
      '4. 此招生范围未能一一尽列所有户籍地址的街、巷、号牌，如需详细了解可向市桥城区教育指导中心咨询。',
    ],
  },
];

const contacts = [
  ['市桥城区教育指导中心', '市桥街、东环街、桥南街、沙头街', '桥南街南珠路65号', '84509135 / 34589568', 'sqedu.pyedu.cn'],
  ['西片教育指导中心', '钟村街、石壁街', '钟村街骏兴路二号', '34770233 / 34715686', 'zcedu.pyedu.cn'],
  ['北片教育指导中心', '大石街、洛浦街', '大石街岗东路175号', '84788564 / 84792984', 'pybpjy.pyedu.cn'],
  ['南村教育指导中心', '南村镇', '南村镇梅山大道南15号', '84763733 / 84763298', 'ncedu.pyedu.cn'],
  ['化龙片教育指导中心', '化龙镇、新造镇、小谷围街', '化龙镇工业路45号之三', '39339973', 'hlpedu.pyedu.cn'],
  ['石楼教育指导中心', '石楼镇', '石楼镇黄山路121号', '34862100 / 34860718', 'sledu.pyedu.cn'],
  ['石碁教育指导中心', '石碁镇、大龙街', '石碁镇富怡路16号', '34560203 / 84551812', 'pysqedu.pyedu.cn'],
  ['沙湾教育指导中心', '沙湾街', '沙湾街沙南永丰路17号（原沙湾成人文化技术学校）', '84731908', 'swjyzdzx.pyedu.cn'],
  ['番禺区教育局', '番禺区', '番禺区清河东路319号区政府办公中心东副楼5楼', '84641656 / 84641676', '—'],
];

// hash 路由下原生 #锚点会与路由冲突，统一用 scrollIntoView 滚动
function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
</script>

<template>
  <section class="policy">
    <header class="page-head">
      <h1>番禺区 2026 年小学招生政策说明</h1>
      <div class="meta">
        <span>发布机构：广州市番禺区教育局</span>
        <span>发布日期：2026-04-29</span>
        <span>依据文件：《2026年番禺区义务教育阶段学校招生计划、招生地段及条件》</span>
      </div>
      <div class="note-tip">
        说明：以下内容为官方文件原文整理。各地段、条件以区教育局当年公布为准；若家长需要针对您家庭的详细情况（户籍、房产、入户年限等）判断入学资格，请直接拨打对应教育指导中心电话咨询。
      </div>
    </header>

    <nav class="toc" aria-label="目录">
      <a v-for="(e, i) in explains" :key="e.id" href="javascript:void(0)" @click="scrollTo(e.id)">
        {{ e.badge.replace('说明 ', '说明') }}<template v-if="e.orange">（市桥城区）</template>
      </a>
      <span class="toc-sep" aria-hidden="true">·</span>
      <a href="javascript:void(0)" @click="scrollTo('contact')">咨询电话</a>
    </nav>

    <section v-for="e in explains" :id="e.id" :key="e.id" class="card">
      <h2><span class="badge" :class="{ orange: e.orange }">{{ e.badge }}</span>{{ e.title }}</h2>
      <p v-for="(p, i) in e.paras" :key="i" :class="{ indent: i > 0 }">{{ p }}</p>
    </section>

    <section id="contact" class="card">
      <h2><span class="badge">咨询</span>各教育指导中心服务范围及招生联系方式</h2>
      <div class="tbl-wrap">
        <table class="contact">
          <thead>
            <tr><th>单位名称</th><th>服务区域</th><th>地址</th><th>联系电话</th><th>网址</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in contacts" :key="c[0]">
              <td>{{ c[0] }}</td><td>{{ c[1] }}</td><td>{{ c[2] }}</td><td>{{ c[3] }}</td>
              <td>{{ c[4] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <footer>
      数据来源：番禺区教育局官网《2026年番禺区义务教育阶段学校招生计划、招生地段及条件》。本页为本地离线材料，内容整理自官方发布，请以区教育局当年正式文件为准。
    </footer>
  </section>
</template>

<style scoped>
.policy { max-width: 820px; margin: 0 auto; line-height: 1.75; font-size: 14px; }

.page-head { background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; padding: 20px 22px 16px; margin-bottom: 16px; }
.page-head h1 { font-size: 20px; font-weight: 700; }
.meta { margin-top: 8px; font-size: 12.5px; color: #6b7280; display: flex; flex-wrap: wrap; gap: 4px 16px; }
.note-tip {
  background: #fdf3e3; border: 1px solid #f2d98a; border-radius: 10px;
  padding: 10px 14px; font-size: 13px; color: #7a5b00; margin-top: 14px;
}

.toc {
  background: #fff; border: 1px solid #e4e3dd; border-radius: 12px;
  padding: 10px 14px; margin-bottom: 14px; font-size: 13px;
  display: flex; flex-wrap: wrap; gap: 6px 10px;
}
.toc a { color: #3a5396; text-decoration: none; }
.toc a:hover { text-decoration: underline; }
.toc-sep { color: #c6cbd1; }

.card { background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; padding: 16px 20px; margin-bottom: 12px; scroll-margin-top: 70px; }
.card h2 {
  font-size: 15px; font-weight: 700; display: flex; align-items: baseline;
  gap: 10px; padding-bottom: 10px; border-bottom: 1px dashed #e4e3dd; margin-bottom: 12px;
}
.badge {
  flex: none; background: #3a5396; color: #fff; border-radius: 6px;
  font-size: 12.5px; font-weight: 600; padding: 1px 8px;
}
.badge.orange { background: #d97706; }
.card p { margin: 8px 0; text-align: justify; }
.card p.indent { padding-left: 1em; }

.tbl-wrap { overflow-x: auto; }
table.contact { width: 100%; border-collapse: collapse; font-size: 13px; }
table.contact th, table.contact td {
  border: 1px solid #e4e3dd; padding: 8px 10px; text-align: left; vertical-align: top;
}
table.contact th { background: #f5f6f8; font-weight: 600; white-space: nowrap; }

footer { text-align: center; font-size: 12px; color: #6b7280; margin-top: 20px; line-height: 1.7; }
</style>
