// @gz/shared 双产物构建：ESM（Web/Vite）+ CJS（原生小程序 require）
import { execSync } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
rmSync(join(here, 'dist'), { recursive: true, force: true });

for (const cfg of ['tsconfig.esm.json', 'tsconfig.cjs.json']) {
  execSync(`npx tsc -p ${cfg}`, { cwd: here, stdio: 'inherit' });
}
// 根 package.json 为 type: module；dist/cjs 需显式标记为 CommonJS 才能被 require
mkdirSync(join(here, 'dist/cjs'), { recursive: true });
writeFileSync(join(here, 'dist/cjs/package.json'), '{"type":"commonjs"}\n');
console.log('[shared] built dist/esm + dist/cjs');
