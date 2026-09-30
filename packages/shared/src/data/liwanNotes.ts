/**
 * 荔湾区单校招生说明补充（转录官方原文，供详情页「招生说明」展示）。
 * 来源：《2026年荔湾区公办初中一年级招生工作方案》（lw.gov.cn post_10791678）三、招生办法第 3 条：
 * 「广州协和学校初中部原则上对口招收广州协和学校小学部毕业生。」
 * 协和小学部 note 为空、初中部 mechanism_note 未含直升条款——在此按 school_id 补充，双端一致。
 */

/** 小学版：协和小学部（school_id → 招生说明补充；note 为空时使用） */
export const liwanPrimaryNoteBySchool: Record<string, string> = {
  'gz-440103-33b32c4c': '广州协和学校初中部原则上对口招收广州协和学校小学部毕业生（小学部直升本校初中部，不参加荔湾区公办初中电脑派位）。',
};

/** 初中版：协和初中部（school_id → 追加到 mechanism_note 的补充条款） */
export const liwanMiddleNoteBySchool: Record<string, string> = {
  'gz-440103-e281e7d0': '广州协和学校初中部原则上对口招收广州协和学校小学部毕业生（本校直升）。',
};
