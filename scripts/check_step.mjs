#!/usr/bin/env node
// check 链单步执行器：通过时只打印一行概要结论；失败时透出完整 stdout/stderr。
// 用法：node scripts/check_step.mjs "<label>" "<shell 命令>"
// 说明：npm run check 中 typecheck / 单测等工具自带逐条详细日志（tsc 无输出、node --test
//   TAP 逐用例打印等），通过时属于噪音；本脚本将成功输出收敛为一行，失败时原样还原
//   全部输出，保证排查信息不丢。
import { spawnSync } from "node:child_process";

const [, , label, command] = process.argv;
if (!label || !command) {
  console.error('用法: node scripts/check_step.mjs "<label>" "<shell 命令>"');
  process.exit(2);
}

const r = spawnSync("/bin/sh", ["-c", command], {
  stdio: ["inherit", "pipe", "pipe"],
  encoding: "utf-8",
});
const log = (r.stdout || "") + (r.stderr || "");

if (r.status === 0) {
  console.log(`✓ ${label} 通过`);
  process.exit(0);
}
console.log(`✗ ${label} 失败（完整日志如下）`);
process.stdout.write(log);
process.exit(r.status === null ? 1 : r.status);
