/** 省市属校区（数据驱动）：dist quota_matrix.campuses，官方汇总表顺序。
 *  id=高中实体 school_id（有实体可跳转），null=实体表缺口校区（官方原文 name 保底展示），
 *  school=归属法人名（官方原文去括号）。quota_matrix.sz（id 键）/sz_schools（原文保底）均引用此表。
 */
export interface CampusInfo {
  /** 高中实体 school_id；null=实体表缺口（如广雅花都/六中从化/六中花都），展示 name 不可跳转 */
  id: string | null;
  /** 官方原文校名（sz_schools 键 / 无实体校区展示名） */
  name: string;
  /** 归属法人名（官方原文去括号，如「华南师范大学附属中学」） */
  school: string;
}
