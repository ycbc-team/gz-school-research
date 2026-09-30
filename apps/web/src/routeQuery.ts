import { watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

/**
 * 明细页筛选/排序状态的 URL 双向同步工具。
 *
 * 背景：小学/初中/高中明细页未做 KeepAlive（控制内存），进入详情页返回时组件会重建，
 * 本地 ref 状态全部丢失。这里把筛选/排序状态写入 URL query：
 * - 进入详情页是 router.push（新历史记录），浏览器后退会恢复上一个 URL（含 query），
 *   组件重建时在 setup 阶段读取 route.query 即可还原筛选/排序；
 * - 状态变化用 router.replace 就地更新 URL，不产生额外历史记录（后退不会逐条回退筛选操作）。
 *
 * @param getQuery 读取当前状态并返回要写入 query 的键值对；值为 undefined/空串的键会被删除（即恢复默认）。
 * @param restore  外部导航改变 query（如导航栏再次点击同路由链接、分享链接直达）且与当前状态
 *                 不一致时回调，页面据此把状态还原到 query 对应值。自己 replace 写入的回显
 *                 （序列化结果与状态一致）会自动跳过，避免循环。
 */
export function useQuerySync(
  getQuery: () => Record<string, string | undefined>,
  restore?: (query: Record<string, unknown>) => void,
) {
  const route = useRoute();
  const router = useRouter();

  // 状态 → URL：就地 replace，不增加历史记录
  watch(getQuery, (q) => {
    router.replace({ query: clean(q) });
  });

  // URL → 状态：外部导航改变 query 时还原；与当前状态序列化一致（即自己写入的回显）则跳过
  watch(
    () => route.query,
    (q) => {
      if (JSON.stringify(q) === JSON.stringify(clean(getQuery()))) return;
      restore?.(q);
    },
    { deep: true },
  );
}

function clean(q: Record<string, string | undefined>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(q)) {
    if (value !== undefined && value !== '') out[key] = value;
  }
  return out;
}

/** 解析 query 单值；缺失或非法返回 fallback。 */
export function queryScalar<T extends string>(value: unknown, valid: readonly T[], fallback: T): T {
  return typeof value === 'string' && (valid as readonly string[]).includes(value) ? (value as T) : fallback;
}

/**
 * 解析 query 逗号分隔集合；缺失/空返回 undefined（表示“全选/不限”）。
 * valid 用于过滤非法成员；不传则原样收下。
 */
export function querySet<T extends string>(value: unknown, valid?: ReadonlySet<T>): Set<T> | undefined {
  if (typeof value !== 'string' || !value) return undefined;
  const set = new Set<T>();
  for (const item of value.split(',')) {
    if (item && (!valid || valid.has(item as T))) set.add(item as T);
  }
  return set.size ? set : undefined;
}
