// -*- coding: utf-8 -*-
/**
 * 紧凑数据编译（compact.mjs）产物一致性检查：真源 data/** 变更后，
 * apps/web/src/data/compact 与 apps/miniprogram/data 必须同步重编译。
 *
 * 做法（与 check_groups_drift.py 的 _replay 同款思路）：
 * 重跑 compact.mjs 到临时目录 → 与入库/入构建链的产物逐文件对比，不一致即失败。
 * 这样"改了 data 忘了跑 compact"会在 npm run check 立即暴露，无需人工记忆。
 *
 * 用法：node scripts/check_compact_drift.mjs
 * 退出码：0 = 产物一致；1 = 存在漂移（列出文件清单 + 首段 diff 摘要）
 */
import { execFileSync } from 'node:child_process';
import { readFileSync, existsSync, readdirSync, statSync, rmSync, mkdtempSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import os from 'node:os';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
// compact.mjs 参数顺序：<主包 cjs> <详情分包 cjs> <web esm>
const TARGETS = [
  { label: 'miniprogram 主包', rel: ['apps', 'miniprogram', 'data'], out: 0 },
  { label: 'miniprogram 详情分包', rel: ['apps', 'miniprogram', 'pages', 'school-detail', 'data'], out: 1 },
  { label: 'web compact', rel: ['apps', 'web', 'src', 'data', 'compact'], out: 2 },
];

function listFiles(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) listFiles(p).forEach((f) => out.push(f));
    else out.push(p);
  }
  return out;
}

// 1) 重跑 compact 到临时目录
const tmp = mkdtempSync(join(os.tmpdir(), 'compact-check-'));
const outTmp = (i) => join(tmp, String(i));
try {
  execFileSync('node', [join(ROOT, 'scripts', 'data', 'compact.mjs'), outTmp(0), outTmp(1), outTmp(2)], {
    stdio: 'pipe',
    encoding: 'utf-8',
  });
} catch (e) {
  console.error('✗ compact.mjs 重跑失败：\n' + (e.stderr || e.message));
  process.exit(1);
}

// 2) 逐目标对比
let failed = 0;
TARGETS.forEach((t) => {
  const targetDir = join(ROOT, ...t.rel);
  const tmpDir = outTmp(t.out);
  if (!existsSync(targetDir)) {
    console.log(`✓ ${t.label}：目录不存在（${join(...t.rel)}），跳过`);
    return;
  }
  const tmpFiles = listFiles(tmpDir);
  const diffs = [];
  const targetFiles = listFiles(targetDir);
  for (const tf of targetFiles) {
    const relF = tf.slice(targetDir.length + 1);
    const cmpF = join(tmpDir, relF);
    if (!existsSync(cmpF)) {
      diffs.push(`  - 产物多余（真源重跑无此文件）: ${relF}`);
      continue;
    }
    if (readFileSync(tf, 'utf8') !== readFileSync(cmpF, 'utf8')) diffs.push(`  ~ 内容不一致: ${relF}`);
  }
  for (const cf of tmpFiles) {
    const relF = cf.slice(tmpDir.length + 1);
    if (!existsSync(join(targetDir, relF))) diffs.push(`  + 产物缺失（真源重跑有，未同步）: ${relF}`);
  }
  if (diffs.length) {
    failed += 1;
    console.error(`✗ ${t.label} 漂移（${diffs.length} 处）：改 data 后未重跑 node scripts/data/compact.mjs`);
    diffs.slice(0, 12).forEach((d) => console.error(d));
  } else {
    console.log(`✓ ${t.label} 与真源一致`);
  }
});

rmSync(tmp, { recursive: true, force: true });
if (failed) {
  console.error('\n修复：node scripts/data/compact.mjs 后重新提交产物。');
  process.exit(1);
}
console.log('\ncompact 产物一致性检查通过');
