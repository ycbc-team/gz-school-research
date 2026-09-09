# -*- coding: utf-8 -*-
"""生成 广州7区59所网传第一梯队小学 法人实体分类结果 entity_classification.json"""
import json, os

BASE = "/Users/bytedance/Developer/gz_school_research"
SRC = os.path.join(BASE, "data/primary/tier1_schools_all.json")
OUT = os.path.join(BASE, "data/primary/entity_classification.json")

# 区教育局官方名单证据（用于佐证区属公办身份）
YUE = {"source": "越秀区政府-越秀区教育集团化办学情况公开", "url": "http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/xqhjthbx/content/post_10874811.html", "note": "区属公办小学名单及教育集团身份"}
YUE_ZS = {"source": "越秀区政府-2023年公办小学招生分组表", "url": "https://www.yuexiu.gov.cn/attachment/7/7294/7294622/8977329.xlsx", "note": "区属公办小学招生分组名单在列"}
BY_PRE = {"source": "白云区政府-2026年义务教育阶段公办学校学位预警通告", "url": "https://www.by.gov.cn/gzbyjy/gkmlpt/content/10/10611/mpost_10611121.html", "note": "白云区教育局公布的区属公办学校名单"}
HP_ZS = {"source": "黄埔区政府-2021年小学一年级招生政策指引", "url": "http://www.hp.gov.cn/hpqgzkfqzdlyzl/jyxx/gzdt/content/post_7264745.html", "note": "黄埔区公办小学招生名单在列"}
PY_ZS = {"source": "番禺区政府-2026年义务教育学校招生工作信息预告", "url": "https://www.panyu.gov.cn/ztzx/qmtjzwgkh/ywjylj/content/post_10681097.html", "note": "番禺区公办小学招生名单在列"}

def ev(source, url, note):
    return {"source": source, "url": url, "note": note}

def school(name, entity_relation, eligible, legal_name, code, ltype, exclude_reason, evidence, opened_year=None):
    return {
        "name": name,
        "entity_relation": entity_relation,
        "tier1_eligible": eligible,
        "legal_entity": {"name": legal_name, "credit_code": code, "type": ltype},
        "exclude_reason": exclude_reason,
        "evidence": evidence,
        "opened_year": opened_year,
    }

schools = []

# ============ 越秀区（6所，全部本部） ============
schools.append(school("广州市越秀区东风东路小学", "本部", True, "广州市越秀区东风东路小学", None, "区属公办", None,
    [ev("越秀区政府-教育集团化办学情况", YUE["url"], "东风东教育集团核心校，名称即品牌源头，传统公办，无他校品牌挂靠；统一社会信用代码待核"), YUE_ZS]))
schools.append(school("广州市越秀区文德路小学", "本部", True, "广州市越秀区文德路小学", None, "区属公办", None,
    [ev("越秀区政府-教育集团化办学情况", YUE["url"], "第二学区学区长学校，传统公办，自身即品牌；统一社会信用代码待核"), YUE_ZS]))
schools.append(school("广州市越秀区东山培正小学", "本部", True, "广州市越秀区东山培正小学", None, "区属公办", None,
    [ev("越秀区政府-教育集团化办学情况", YUE["url"], "东山培正教育集团核心校/培正教育集团成员校，百年品牌源头即自身；统一社会信用代码待核"), YUE_ZS]))
schools.append(school("广州市越秀区小北路小学", "本部", True, "广州市越秀区小北路小学", None, "区属公办", None,
    [ev("越秀区政府-教育集团化办学情况", YUE["url"], "第五学区学区长学校，传统公办，自身即品牌；统一社会信用代码待核"), YUE_ZS]))
schools.append(school("广州市越秀区农林下路小学", "本部", True, "广州市越秀区农林下路小学", None, "区属公办", None,
    [ev("越秀区政府-教育集团化办学情况", YUE["url"], "第三学区副学区长学校，传统公办，自身即品牌；统一社会信用代码待核"), YUE_ZS]))
schools.append(school("广州市越秀区铁一小学", "本部", True, "广州市越秀区铁一小学", None, "区属公办", None,
    [ev("越秀区政府-教育集团化办学情况", YUE["url"], "铁一小学教育集团核心校，越秀区属公办小学（校名源自铁路系统，非铁一中学附属/挂牌），自身即品牌；统一社会信用代码待核"), YUE_ZS]))

# ============ 荔湾区（4所） ============
schools.append(school("广州市荔湾区乐贤坊小学", "本部", True, "广州市荔湾区乐贤坊小学", None, "区属公办", None,
    [ev("今日头条-2023年11月荔湾区集团化办学方案转载", "http://m.toutiao.com/group/7304613843852886582/", "授权制小学教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州协和学校（小学部，原广州市协和小学）", "同法人校区", True, "广州协和学校", None, "市属公办", None,
    [ev("广州协和学校官网-学校简介", "https://www.gzxhhs.edu.cn/Category_99/Index.aspx", "2022年广州市协和小学整体并入市协和中学，成立广州协和学校（广州市教育局直属十二年一体化公办学校），小学部与中学部同属一个法人；信用代码待核"),
     ev("南方+", "http://static.nfapp.southcn.com/content/202208/31/c6845401.html", "2022年8月31日广州协和学校揭牌，协和小学整体并入协和中学，合并后为新法人（市直属）")],
    None))
schools.append(school("广州市荔湾区沙面小学", "本部", True, "广州市荔湾区沙面小学", None, "区属公办", None,
    [ev("今日头条-2023年11月荔湾区集团化办学方案转载", "http://m.toutiao.com/group/7304613843852886582/", "沙面小学教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市荔湾区康有为纪念小学", "本部", True, "广州市荔湾区康有为纪念小学", None, "区属公办", None,
    [ev("今日头条-2023年11月荔湾区集团化办学方案转载", "http://m.toutiao.com/group/7304613843852886582/", "授权制小学教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))

# ============ 海珠区（4所） ============
schools.append(school("广州市海珠区实验小学（穗花校区/富基校区）", "同法人校区", True, "广州市海珠区实验小学", "12440105455369568T", "区属公办", None,
    [ev("360地图-海珠区实验小学工商信息", "https://m.map.360.cn/m/search/detail/pid=1af65024e37663c7", "统一社会信用代码12440105455369568T，同一事业单位法人名下穗花、富基两校区"),
     ev("信息时报", "http://m.toutiao.com/group/6592453772352422413/", "富基校区2018年9月开学（原富基广场配套小学烂尾14年后续建），穗花校区即原穗花小学（本部）"),
     ev("海珠区政府-公办小学地址电话一览表", "https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10238/mpost_10238488.html", "穗花校区、富基校区均以'广州市海珠区实验小学'名义招生")],
    2018))
schools.append(school("广州市海珠区同福中路第一小学", "本部", True, "广州市海珠区同福中路第一小学", None, "区属公办", None,
    [ev("海珠区政府-集团化办学报道", "https://www.haizhu.gov.cn/hzdt/hzyw/hzzc/content/mpost_10167355.html", "同福中路第一小学教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市海珠区宝玉直小学", "本部", True, "广州市海珠区宝玉直小学", None, "区属公办", None,
    [ev("广州日报-2024年海珠区教育集团化办学报道", "http://m.toutiao.com/group/7359548544342278695/", "宝玉直小学与宝玉直实验小学为两所不同学校（后者为宝实教育集团核心校）；本条目为宝玉直小学本体，传统公办；统一社会信用代码待核")]))
schools.append(school("广州市海珠区昌岗中路小学", "本部", True, "广州市海珠区昌岗中路小学", None, "区属公办", None,
    [ev("广州日报大洋网-2025年昌岗中路小学教育集团成立", "http://news.dayoo.com/gzrbrmt/202511/13/170614_54893958.htm", "昌岗中路小学教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))

# ============ 天河区（6所） ============
schools.append(school("华南师范大学附属小学", "本部", True, "华南师范大学附属小学", "12440000G184654781", "省属公办", None,
    [ev("华师附小官网-校史回顾", "http://hnsdfx.scnu.edu.cn/xuexiaogaikuang/xiaoshihuigu/", "广东省唯一省直属小学，由省教育厅与华南师范大学双重领导，省属高校直属附属，品牌源头即自身（本部）"),
     ev("企查查", "https://m.qcc.com/firm/g570904b56e48e5ff358a859d90aeab9.html", "统一社会信用代码12440000G184654781，广东省事业单位登记管理局登记")]))
schools.append(school("广州市天河区华阳小学", "本部", True, "广州市天河区华阳小学", None, "区属公办", None,
    [ev("南方+", "http://static.nfapp.southcn.com/content/201809/08/c1471451.html", "广州华阳教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市天河区华景小学", "本部", True, "广州市天河区华景小学", None, "区属公办", None,
    [ev("无忧考网-2016年天河区小学排名", "https://m.51test.net/show/8034450.html", "天河区传统公办名校，自身即品牌，未见他校品牌挂靠；统一社会信用代码待核")]))
schools.append(school("广州市天河区龙口西小学", "本部", True, "广州市天河区龙口西小学", None, "区属公办", None,
    [ev("搜狐网-2016年广州小学梯队", "https://m.sohu.com/n/457616886/", "天河区传统公办名校，自身即品牌，未见他校品牌挂靠；统一社会信用代码待核")]))
schools.append(school("广州市天河区天府路小学", "本部", True, "广州市天河区天府路小学", None, "区属公办", None,
    [ev("网易-2020年天河区'超级小学'", "https://c.m.163.com/news/a/FFV62B1R0530MA7O.html", "天河区传统公办名校，自身即品牌，未见他校品牌挂靠；统一社会信用代码待核")]))
schools.append(school("广州市天河区体育东路小学（含兴国学校、海明学校）", "本部", True, "广州市天河区体育东路小学", None, "区属公办", None,
    [ev("云上岭南（羊城晚报）", "https://ysln.ycwb.com/content/2024-10/28/content_53014437.html", "体育东路小学本体1990年创办；2018年体育东教育集团成立后，兴国校区、海明校区独立办学为'体育东路小学兴国学校''体育东路小学海明学校'，与本体分属不同办学主体，本条目为体育东路小学本体→本部；兴国/海明学校法人性质待核"),
     ev("南方+", "https://www.nfnews.com/content/j3kjkPqdyA.html", "兴国学校、海明学校、均和小学均为体育东'手把手'创办的新校，灵秀小学为参与筹建独立开办；均属集团化办学下新设学校")]))

# ============ 白云区（13所） ============
schools.append(school("广州市白云区京溪小学", "本部", True, "广州市白云区京溪小学", None, "区属公办", None,
    [ev("白云区政府-2026年学位预警通告", BY_PRE["url"], "白云区教育局公布的区属公办学校；京溪小学教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市白云区景泰小学", "本部", True, "广州市白云区景泰小学", None, "区属公办", None,
    [ev("工人日报-2024年景泰小学教育集团", "https://www.workercn.cn/c/2024-03-08/8177646.shtml", "景泰小学教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市白云区广园小学", "本部", True, "广州市白云区广园小学", None, "区属公办", None,
    [ev("广州日报大洋网-2024年白云区教育集团", "http://news.dayoo.com/guangzhou/202403/12/139995_54641238.htm", "广园小学教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市白云区黄边小学", "本部", True, "广州市白云区黄边小学", None, "区属公办", None,
    [ev("白云区政府-2024年学位预警通告", "https://www.by.gov.cn/gzbyjy/gkmlpt/content/9/9472/mpost_9472287.html", "白云区教育局公布的区属公办学校；传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市白云区三元里小学", "本部", True, "广州市白云区三元里小学", None, "区属公办", None,
    [ev("今日头条-三元里小学教育集团", "http://m.toutiao.com/group/7329489222564676131/", "三元里小学教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市白云区华师附中实验小学", "独立法人挂牌校", False, "广州市白云区华师附中实验小学", "12440111550572636K", "区属公办",
    "白云区属公办小学，借用华南师范大学附属中学名校品牌（华师附中教育集团成员、华师附中承办），独立事业单位法人，本质为合作办学挂牌校",
    [ev("白云区政府-2026年部门预算", "https://www.by.gov.cn/attachment/8/8008/8008982/10779110.pdf", "白云区教育局下属公办小学，全额拨款事业单位"),
     ev("上哪学", "https://www.shangnaxue.net/school/1174882464294817794.html?cid=105", "2009年7月由白云区政府、白云区教育局、华师附中教育集团、新世界中国地产联合开办，华师附中承办"),
     ev("企查查", "https://m.qcc.com/firm/g837c9fddcbdc841794b719673ce0912.html", "统一社会信用代码12440111550572636K，独立事业单位法人（不同于华师附中本体）")],
    2009))
schools.append(school("广州市白云区同和小学", "本部", True, "广州市白云区同和小学", None, "区属公办", None,
    [ev("白云区政府-2026年学位预警通告", BY_PRE["url"], "白云区教育局公布的区属公办学校；传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市白云区握山小学", "本部", True, "广州市白云区握山小学", None, "区属公办", None,
    [ev("白云区政府-2026年学位预警通告", BY_PRE["url"], "白云区教育局公布的区属公办学校；传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市白云区明德小学", "本部", True, "广州市白云区明德小学", None, "区属公办", None,
    [ev("搜狐-2019幼升小名校解读（白云区）", "https://m.sohu.com/a/245192768_349684", "白云区传统公办小学，自身即品牌，未见他校品牌挂靠；统一社会信用代码待核")]))
schools.append(school("广州市白云区人和镇第二小学", "本部", True, "广州市白云区人和镇第二小学", None, "区属公办", None,
    [ev("搜狐-2019幼升小名校解读（白云区）", "https://m.sohu.com/a/245192768_349684", "白云区传统公办小学，自身即品牌，未见他校品牌挂靠；统一社会信用代码待核")]))
schools.append(school("广州市白云区江村小学", "本部", True, "广州市白云区江村小学", None, "区属公办", None,
    [ev("搜狐-2019幼升小名校解读（白云区）", "https://m.sohu.com/a/245192768_349684", "白云区传统公办小学，自身即品牌，未见他校品牌挂靠；统一社会信用代码待核")]))
schools.append(school("广州市白云区太和第一小学", "本部", True, "广州市白云区太和第一小学", "12440111G34038388Y", "区属公办", None,
    [ev("启信宝", "https://www.qixin.com/company/01cf8460-f177-11e9-8ce2-00163e0d7703", "统一社会信用代码12440111G34038388Y，举办单位为白云区教育局，单一事业单位法人"),
     ev("白云区政府-义务教育学校基本信息一览表", "https://www.by.gov.cn/gzbyjy/gkmlpt/content/8/8787/post_8787737.html", "官方一览表显示和龙校区属于'太和第二小学'（米龙/白山/和龙校区）而非太和第一小学；太和第一小学为1994年开办的单校区镇属中心小学，判为本部")]))
schools.append(school("广州市白云区民航学校（校本部·小学部）", "本部", True, "广州市白云区民航学校", None, "区属公办", None,
    [ev("白云区政府-2025年部门预算", "https://www.by.gov.cn/attachment/7/7853/7853809/10373821.pdf", "白云区教育局属下公办九年一贯制学校，含小学教育（2050202）"),
     ev("广州白云发布", "http://m.toutiao.com/group/7542884961125138986/", "原名民航广州子弟学校（1984年成立），2019年7月移交白云区人民政府转为九年一贯制公办；民航系统背景，自身即品牌，无他校品牌挂靠。注：源调研conclusion为'不支撑'（第一梯队传闻），entity层面判本部")]))

# ============ 黄埔区（11所） ============
schools.append(school("广州市黄埔区怡园小学（东、西、北校区）", "同法人校区", True, "广州市黄埔区怡园小学", "12440112G34045190C", "区属公办", None,
    [ev("360地图/比地招标网-怡园小学工商信息", "https://m.map.360.cn/m/search/detail/pid=f01a185eca47c3f3", "统一社会信用代码12440112G34045190C，'怡园小学'单一事业单位法人（1989年创办）"),
     ev("黄埔区政府-2022年小学招生政策指引", "https://www.hp.gov.cn/gzhpjy/gkmlpt/content/8/8220/mpost_8220896.html", "东、西、北三个校区均以'怡园小学'名义招生，同法人多校区办学")]))
schools.append(school("广州市黄埔区荔园小学", "本部", True, "广州市黄埔区荔园小学", None, "区属公办", None,
    [ev("黄埔区政府-2021年小学招生政策指引", HP_ZS["url"], "黄埔区公办小学；传统公办，自身即品牌，未见他校品牌挂靠；统一社会信用代码待核")]))
schools.append(school("广州市黄埔区港湾小学", "本部", True, "广州市黄埔区港湾小学", None, "区属公办", None,
    [ev("搜狐-黄埔区热门公办小学", "https://m.sohu.com/a/356749053_679233/", "黄埔区传统公办小学，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市黄埔区下沙小学", "本部", True, "广州市黄埔区下沙小学", None, "区属公办", None,
    [ev("凤凰网房产广州-省一级学区房盘点", "https://gz.ihouse.ifeng.com/news/2019_07_01-52156256_0.shtml", "老黄埔传统公办省一级小学，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市黄埔区文冲小学", "本部", True, "广州市黄埔区文冲小学", None, "区属公办", None,
    [ev("黄埔区政府-2021年小学招生政策指引", HP_ZS["url"], "黄埔区公办小学；传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市黄埔区沙步小学", "本部", True, "广州市黄埔区沙步小学", None, "区属公办", None,
    [ev("今日头条-黄埔37所知名小学盘点", "http://m.toutiao.com/group/7173958017585594884/", "黄埔区传统公办小学，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州石化小学（东、西校区）", "同法人校区", True, "广州石化小学", "124401127812403809", "区属公办", None,
    [ev("启信宝/天眼查", "https://m.qixin.com/company/89a1e152-1e84-48ed-b348-13aa8f5fb8a5", "统一社会信用代码124401127812403809，举办单位为黄埔区教育局，单一事业单位法人"),
     ev("黄埔区政府-2021年小学招生政策指引", HP_ZS["url"], "广州石化小学公办小学，东、西校区同法人办学")]))
schools.append(school("广州市黄埔区东荟花园小学（东、南、北校区）", "同法人校区", True, "广州市黄埔区东荟花园小学", "12440112078437915D", "区属公办", None,
    [ev("启信宝/企查查", "https://m.qixin.com/company/f2859228-fd16-11e9-9b97-00163e08d0d2", "统一社会信用代码12440112078437915D（曾用名广州市萝岗区东荟花园小学），单一事业单位法人"),
     ev("本地宝-2023年黄埔区公办小学名单", "http://gz.bendibao.com/life/202329/334770.shtml", "东、南、北三个校区均以'东荟花园小学'名义招生，同法人多校区办学")]))
schools.append(school("广州市黄埔区玉泉学校（小学部）", "本部", True, "广州市黄埔区玉泉学校", "12440112MB2C09042H", "区属公办", None,
    [ev("黄埔区政府-2023年部门预算", "http://www.hp.gov.cn/attachment/7/7431/7431878/8963542.pdf", "黄埔区教育局属下公办九年一贯制学校"),
     ev("天眼查", "https://m.tianyancha.com/company/3096966758", "统一社会信用代码12440112MB2C09042H，举办单位黄埔区教育局"),
     ev("今日头条-黄埔镜像", "http://m.toutiao.com/group/7655667017337111092/", "隶属玉岩教育集团（集团成员身份），但校名无'玉岩'等名校品牌挂靠，2016年建校自有品牌，判为本部")]))
schools.append(school("广州市黄埔区香雪小学", "本部", True, "广州市黄埔区香雪小学", None, "区属公办", None,
    [ev("今日头条-黄埔37所知名小学盘点", "http://m.toutiao.com/group/7173958017585594884/", "黄埔区传统公办小学，自身即品牌；统一社会信用代码待核。注：源调研conclusion为'不支撑'")]))
schools.append(school("广州市黄埔区黄埔军校小学", "独立法人挂牌校", False, "广州市黄埔区黄埔军校小学", "12440112MB2D378101", "区属公办",
    "黄埔区属公办小学，由广州大学附属中学委托管理（黄埔广附教育集团核心校），独立事业单位法人，借用广大附中办学品牌",
    [ev("南方+-黄埔广附教育集团授牌", "https://m.sohu.com/a/395645195_272871/", "黄埔广附教育集团核心校，广大附中委托管理"),
     ev("企查查/天眼查", "https://m.qcc.com/firm/gb7f4f132b2469f83b279e530e40f8ac.html", "统一社会信用代码12440112MB2D378101，黄埔区事业单位登记管理局登记，独立法人（不同于广大附中）")],
    None))

# ============ 番禺区（15所） ============
schools.append(school("广州市番禺区市桥中心小学", "本部", True, "广州市番禺区市桥中心小学", None, "区属公办", None,
    [ev("番禺区政府-2026年招生信息预告", PY_ZS["url"], "番禺区公办小学；传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市番禺区市桥东城小学", "本部", True, "广州市番禺区市桥东城小学", None, "区属公办", None,
    [ev("搜狐-番禺11所省级小学盘点", "https://m.sohu.com/a/163641170_689549/", "番禺区传统公办小学，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市番禺区市桥南阳里小学", "本部", True, "广州市番禺区市桥南阳里小学", None, "区属公办", None,
    [ev("搜狐-番禺11所省级小学盘点", "https://m.sohu.com/a/163641170_689549/", "番禺区传统公办小学，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市番禺区市桥德兴小学", "本部", True, "广州市番禺区市桥德兴小学", None, "区属公办", None,
    [ev("番禺区政府-德兴小学教育集团", "http://www.panyu.gov.cn/zwgk/zfxxgkml/xxgkml/zwdt/fzxw/content/post_10033795.html", "德兴小学教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市番禺区市桥北城小学", "本部", True, "广州市番禺区市桥北城小学", None, "区属公办", None,
    [ev("番禺区政府-2026年招生信息预告", PY_ZS["url"], "番禺区公办小学；传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市番禺区市桥实验小学", "本部", True, "广州市番禺区市桥实验小学", None, "区属公办", None,
    [ev("番禺区政府-2023年新成立教育集团", "https://www.panyu.gov.cn/zwgk/zfxxgkml/xxgkml/zwdt/fzxw/content/post_9157738.html", "市桥实验小学教育集团核心校，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广东番禺中学附属学校（小学部）", "独立法人挂牌校", False, "广东番禺中学附属学校", "12440113MB2C79294W", "区属公办",
    "番禺区属九年一贯制公办学校（独立法人），借用广东番禺中学品牌（广东番禺中学教育集团成员），小学部非番禺中学本部",
    [ev("启信宝/企查查", "https://www.qixin.com/company/8e775174-f094-11e9-a33c-00163f00240b", "统一社会信用代码12440113MB2C79294W，举办单位为番禺区教育局，2022年6月登记成立"),
     ev("广州市生态环境局-环评文件", "https://sthjj.gz.gov.cn/attachment/7/7279/7279468/8920355.pdf", "广东番禺中学自身统一社会信用代码为12440113455410604B，与附属学校不同→独立法人挂牌校"),
     ev("羊城晚报-广东番禺中学教育集团", "http://m.toutiao.com/group/7100340799665078819/", "集团2019年成立，附属学校为集团成员，借用番禺中学品牌")],
    None))
schools.append(school("广东仲元中学附属学校（小学部）", "独立法人挂牌校", False, "广东仲元中学附属学校", "12440113MB2D67737Q", "区属公办",
    "番禺区属九年一贯制公办学校（独立法人），借用广东仲元中学品牌（仲元附属学校教育集团核心校），小学部非仲元中学本部",
    [ev("企查查/番禺区事业单位登记信息", "https://m.qcc.com/firm/gbac5fbfbb64670ec7a941f2291330cf.html", "统一社会信用代码12440113MB2D67737Q，番禺区事业单位登记管理局登记"),
     ev("启信宝-广东仲元中学", "https://www.qixin.com/company/5204f8a6-63b7-11e8-be23-00163e104bc8", "广东仲元中学自身统一社会信用代码为12440113455409144C，与附属学校不同→独立法人挂牌校"),
     ev("番禺区政府-仲元附属学校教育集团", "http://www.panyu.gov.cn/zwgk/zfxxgkml/xxgkml/zwdt/fzxw/content/post_10033795.html", "仲元附属学校教育集团核心校")],
    None))
schools.append(school("广州市番禺区石碁镇中心小学", "本部", True, "广州市番禺区石碁镇中心小学", None, "区属公办", None,
    [ev("搜狐-番禺11所省级小学盘点", "https://m.sohu.com/a/163641170_689549/", "番禺区镇属中心小学，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市番禺区石楼镇中心小学", "本部", True, "广州市番禺区石楼镇中心小学", None, "区属公办", None,
    [ev("搜狐-番禺11所省级小学盘点", "https://m.sohu.com/a/163641170_689549/", "番禺区镇属中心小学，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市番禺区南村镇中心小学", "本部", True, "广州市番禺区南村镇中心小学", None, "区属公办", None,
    [ev("搜狐-番禺11所省级小学盘点", "https://m.sohu.com/a/163641170_689549/", "番禺区镇属中心小学，传统公办，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市番禺区洛溪新城小学", "本部", True, "广州市番禺区洛溪新城小学", None, "区属公办", None,
    [ev("今日头条-丽丽在广州（广州11区小学排名汇总）", "http://m.toutiao.com/group/7488552224281346579/", "番禺区传统公办小学，自身即品牌；统一社会信用代码待核")]))
schools.append(school("广州市番禺区华师附中番禺小学", "独立法人挂牌校", False, "华师附中番禺小学", "12440113MB2E14839T", "区属公办",
    "番禺区属公办小区配套小学（2021年开办、2023年更名），纳入华师附中教育集团，独立事业单位法人，借用华师附中品牌",
    [ev("广州本地宝-2026年教师招聘公告", "https://m.gz.bendibao.com/job/364610.html", "小区配套公办小学，2021年9月1日开办，2023年4月28日正式更名为华师附中番禺小学并纳入华师附中教育集团"),
     ev("爱企查/企查查", "https://www.aiqicha.com/company_detail_87503662747695", "统一社会信用代码12440113MB2E14839T，独立事业单位法人"),
     ev("华南师范大学附属中学官网", "https://www.hsfz.net.cn/list_6/5652.html", "华师附中教育集团成员校，集团化办学。注：另有一所2003年创办的民办'华师附中番禺小学'（华南新城内，现名广州南方学院番禺附属小学），与本条公办校为不同主体，本条目指公办校")],
    2021))
schools.append(school("广州大学附属小学", "独立法人挂牌校", False, "广州大学附属小学", "1244011307461868XG", "区属公办",
    "番禺区属公办小学（番禺区教育局、广州大学附属中学、小谷围街道三方合作办学），由广大附中负责全面管理，独立事业单位法人，借用广大附中品牌",
    [ev("番禺区政府-2026年部门预算", "http://www.panyu.gov.cn/attachment/7/7982/7982360/10713893.pdf", "2013年8月成立，大学城地区配套公办小学"),
     ev("广州大学就业网", "https://jy.gzhu.edu.cn/web/Index/company-info?id=67973", "番禺区教育局、小谷围街道办和广州大学附属中学合作办学，为广大附中教育集团成员单位，由广大附中负责实施教育教学全面管理"),
     ev("天眼查", "https://m.tianyancha.com/company/3096983979", "统一社会信用代码1244011307461868XG，番禺区事业单位登记管理局登记")],
    2013))
schools.append(school("华南师范大学附属广州大学城小学", "独立法人挂牌校", False, "华南师范大学附属广州大学城小学", "12440113MB2C97994M", "区属公办",
    "番禺区属公办小学（番禺区教育局、华南师范大学、小谷围街道三方合作创办），由华师附小全面管理（垂直管理），独立事业单位法人，借用华师附小品牌",
    [ev("番禺区政府-2026年部门预算", "http://www.panyu.gov.cn/attachment/7/7981/7981020/10709056.pdf", "番禺区教育局、华南师范大学、小谷围街道办事处三方合作创办的全日制公办小学"),
     ev("高校人才网-2025年招聘公告", "https://www.gaoxiaojob.com/announcement/detail/322068.html", "华南师范大学附属小学垂直管理学校，由华师附小负责全面管理"),
     ev("启信宝", "https://www.qixin.com/company/18d23e84-f18e-11e9-8253-00163f00240b", "统一社会信用代码12440113MB2C97994M，独立事业单位法人"),
     ev("羊城晚报·羊城派", "http://m.toutiao.com/group/7387766445645546036/", "2018年6月创办，2018年秋季招生")],
    2018))

assert len(schools) == 59, f"学校数量错误: {len(schools)}"

# 校验name与源JSON完全一致
with open(SRC, "r", encoding="utf-8") as f:
    src = json.load(f)
src_names = [s["name"] for d in src["districts"].values() for s in d["schools"]]
out_names = [s["name"] for s in schools]
assert sorted(src_names) == sorted(out_names), "name与源JSON不一致"
for n in src_names:
    assert n in out_names, f"缺少: {n}"

result = {"title": "广州7区59所网传第一梯队小学-法人实体分类", "generated_date": "2026-09-09", "schools": schools}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"已写入 {OUT}，共 {len(schools)} 所")

# ===== 统计摘要 =====
from collections import Counter, defaultdict
cnt_rel = Counter(s["entity_relation"] for s in schools)
print("\n=== 分类统计（按类别） ===")
for k, v in cnt_rel.items():
    print(f"  {k}: {v}")

# 按区×类别
by_dist = defaultdict(Counter)
dist_map = {}
for dname, dval in src["districts"].items():
    for s in dval["schools"]:
        dist_map[s["name"]] = dname
for s in schools:
    by_dist[dist_map[s["name"]]][s["entity_relation"]] += 1
print("\n=== 分类统计（按区×类别） ===")
print("区       | 本部 | 同法人校区 | 独立法人挂牌校 | 待核 | 合计")
for d in ["越秀区", "荔湾区", "海珠区", "天河区", "白云区", "黄埔区", "番禺区"]:
    c = by_dist[d]
    print(f"{d} | {c.get('本部',0)} | {c.get('同法人校区',0)} | {c.get('独立法人挂牌校',0)} | {c.get('待核',0)} | {sum(c.values())}")

print("\n=== 独立法人挂牌校清单（tier1_eligible=false） ===")
for s in schools:
    if s["entity_relation"] == "独立法人挂牌校":
        print(f"  - {s['name']} | 信用代码: {s['legal_entity']['credit_code']}")

print("\n=== 待核清单 ===")
pending = [s["name"] for s in schools if s["entity_relation"] == "待核"]
print("  " + ("无" if not pending else "、".join(pending)))
