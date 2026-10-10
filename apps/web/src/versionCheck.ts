/**
 * 发版检测：轮询比对构建产物 version.json（内容 = 产物 hash，见 vite.config.ts
 * versionJsonPlugin），发现新版直接 reload——部署后旧页面自动切到新版，
 * 避免 GitHub Pages 整体替换后旧页面引用旧 chunk 404、点击跳转失效。
 *
 * 兼容性：
 * - 仅生产构建启用（main.ts 按 import.meta.env.PROD 调用）；
 * - file:// 直接打开时 fetch 失败会静默跳过，不影响本地打开能力；
 * - 版本文件请求带 ?t= 与 cache:'no-store'，保证拿到的是最新版而非缓存。
 */

const VERSION_URL = './version.json';
/** 轮询间隔：60s（页面可见时另有即时核对，浏览器后台节流也不影响） */
const POLL_INTERVAL_MS = 60_000;

let currentVersion: string | null = null;
let timer: number | null = null;

async function fetchVersion(): Promise<string | null> {
  try {
    const res = await fetch(`${VERSION_URL}?t=${Date.now()}`, { cache: 'no-store' });
    if (!res.ok) return null;
    const data = (await res.json()) as { version?: unknown };
    return typeof data.version === 'string' ? data.version : null;
  } catch {
    // file:// / 开发环境 / 网络异常：静默跳过，不打扰用户
    return null;
  }
}

async function checkOnce(): Promise<void> {
  const latest = await fetchVersion();
  if (latest == null) return;

  if (currentVersion == null) {
    // 首次拿到版本：记录并启动轮询
    currentVersion = latest;
    timer = window.setInterval(() => void checkOnce(), POLL_INTERVAL_MS);
    return;
  }

  if (latest !== currentVersion) {
    if (timer != null) window.clearInterval(timer);
    // 部署切换：立即刷新到新版。reload 后 version.json 即新值，不会重复触发。
    window.location.reload();
  }
}

export function startVersionCheck(): void {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  void checkOnce();
  // 页面从后台切回前台时立即核对（后台定时器可能被浏览器节流/挂起）
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') void checkOnce();
  });
}
