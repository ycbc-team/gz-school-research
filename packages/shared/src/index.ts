/**
 * @gz/shared —— 双端共享核心包（类型 + 纯逻辑，零 DOM/平台依赖）。
 * 数据不内嵌：各端自行从 data/*.json（唯一真源）加载后调用本包函数。
 */
export * from './types.js';
export * from './const.js';
export * from './geo.js';
export * from './stats.js';
export * from './support.js';
export * from './format.js';
export * from './compact.js';
