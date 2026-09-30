// @gz/shared 双产物构建：ESM（Web/Vite）+ CJS（原生小程序 require）
import { execSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
// npm ci 干净安装会把 typescript hoist 到根 node_modules（shared/node_modules/typescript
// 不存在），硬编码相对路径会让 CI 构建失败（本地旧 node_modules 布局侥幸通过）。
// createRequire.resolve 沿 node_modules 向上解析，兼容 hoisted / 嵌套两种布局。
const require = createRequire(import.meta.url);
const tsc = require.resolve('typescript/bin/tsc');
rmSync(join(here, 'dist'), { recursive: true, force: true });

for (const cfg of ['tsconfig.esm.json', 'tsconfig.cjs.json']) {
  execSync(`node "${tsc}" -p ${cfg}`, { cwd: here, stdio: 'inherit' });
}
// 根 package.json 为 type: module；dist/cjs 需显式标记为 CommonJS 才能被 require
mkdirSync(join(here, 'dist/cjs'), { recursive: true });
writeFileSync(join(here, 'dist/cjs/package.json'), '{"type":"commonjs"}\n');
console.log('[shared] built dist/esm + dist/cjs');
