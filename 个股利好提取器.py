# -*- coding: utf-8 -*-
"""
个股利好提取器 v2.4
====================
自动/手动抓取财经快讯 -> 提取个股层面利好与利空 -> 五级评级 + 两层级跟踪 ->
结合个股真实涨跌做市场验证 -> 生成细化报告(md + html) + 沪深主板代码清单 -> 记录历史提取记录。

评级体系：
  利好五级，并归入『订单落地』/『概念发酵』两个层级：
    L5 硬利好   订单/合同中标签署、增持/回购/分红（事件已确认，可计入业绩与股东回报）
    L4 准硬利好 量产/交付/获批/投产等产能资质落地
    L3 强催化   扩产投资/定增合资，以及"拟回购/拟增持"等未落地资本动作
    L2 软利好   合作合资融资、经营改善、产品发布上线
    L1 传闻预期 传闻/据悉/有望/拟/计划等未证实信息
  利空三级：
    N3 重大利空 立案调查、退市风险警示、股权冻结、实控人被查
    N2 实质利空 减持、处罚警示、业绩暴雷、合作终止
    N1 软利空   小比例减持、常规问询函、澄清辟谣
  同一事件命中多个利空类别时取最严重；有明显利空的个股不再计入利好（利好利空互斥）。

市场验证（v2.0 新增）：
  每条明细补 T 日 / T+1 涨跌幅与相对基准指数（沪→上证指数 / 深北→深证综指）的超额收益，
  并给出『强验证 / 弱验证 / 中性 / 背离 / 显著背离 / 待验证』标签，用于回看评级是否站得住。

回测调档（v2.0 新增）：
  --review 用近 30 天回补缓存 + 真实 T+1 超额收益反过来校验评级规则，并"按当前规则重新打分"
  （调档前后可直接对比同一份报告）。据此生效的证据层：弱证据词（拟/量产/投产/出货/订单/
  合作协议）降一级，命中强证据词（回购/增持/收购/回升）的条目豁免降级；担保/质押/贷款类
  文案整类剔除；利空侧『冻结/司法/担保』由 N3 降为 N2。入表门槛为样本 ≥20 且两次回测方向
  一致 —— 该门槛挡住了 23 日样本中"增资 5 条 100%"这类小样本假信号。

归属修正（v2.1）：
  1) 通用词型名称（老百姓/机器人/太阳能…）只认"紧跟冒号或公告/股份/集团"与"顿号并列个股"
     两类形式证据，不再采信"句首/标点前"和"前文出现公告/收购"—— 财政部购房贴息答记者问里的
     普通名词"老百姓"曾因此挂到 603883；"杭州宇树机器人有限公司"这类同名不同司也一并挡掉；
  2) 非个股文案整条剔除：宏观政策问答/解读（答记者问等）、盘面异动与热点汇总
     （"XX概念震荡走高 YY涨停"、A股午评、主力资金、概念股综述）；
  3) 『订单/合同』需同时出现实词（订单/中标/供货/框架协议…）或金额，只有"签订/合同"这类
     弱动词时不计入该类别；
  4) 机构观点/研报条（【机构：观点】且非该机构自身事项）里被点到的个股降一级、层级固定概念发酵。

功能模式：
  python 个股利好提取器.py            # 手动立即提取一次（近24小时滚动窗口）
  python 个股利好提取器.py --date 20260918   # 手动提取指定日期数据
  python 个股利好提取器.py --backfill 30    # 批量回补最近30天（逐日报告 + 结构化缓存 + 行情验证）
  python 个股利好提取器.py --review         # 按回补缓存生成《规则回测》报告（默认近30天）
  python 个股利好提取器.py --verify-selftest # 行情解析自测（注入坏样本，校验异常能被识别）
  python 个股利好提取器.py --auto     # 常驻运行，每天 00:15 自动提取前一日数据
  python 个股利好提取器.py --install-task   # 注册 Windows 计划任务(每天00:15)，无需常驻
  python 个股利好提取器.py --remove-task    # 删除已注册的计划任务
  python 个股利好提取器.py --history  # 查看历史提取记录
  python 个股利好提取器.py --run      # 同默认，手动立即提取一次
  python 个股利好提取器.py --update-stocks  # 强制刷新全量A股代码表

说明：
  - 纯 Python 标准库实现，无需 pip 安装任何第三方包；
  - 联网抓取多源财经快讯(东方财富/新浪财经/华尔街见闻/财联社)与官方公告(巨潮资讯网)，某源失败自动跳过；
  - 时间窗口：默认取"最近24小时"滚动窗口；--date 指定日期时取该日 00:00~24:00。
    快讯源逐页(page/cursor/last_time)回溯，最多回溯 10 天；巨潮公告按 seDate 直查官方存档，
    可回溯 30 天，故超过 10 天的历史日期只取巨潮公告；
    东方财富快讯接口无翻页游标（实测），历史日期下不参与回溯，报告"抓取来源"里如实标注；
    某源翻页上限已到而取不到数据时，同样如实标注，绝不用"最新一页"冒充该日数据。
  - 各快讯源独立翻页，故并行抓取（历史日期总耗时约等于最慢的那个源）；
  - 使用关键词规则提取个股利好并分类，识别股票代码；
  - 套壳/程式化公告（募集资金监管协议、回购前十大股东持股情况、限制性股票回购注销、通知债权人、
    中介机构意见书、回购进展等）不计入利好，他人事件误挂到本股的条目直接剔除；
  - 股票识别基于全量A股代码表(约5500只，含沪/深/京)，首次运行自动联网抓取并缓存，
    之后每 30 天自动更新；联网失败时回退到打包内置的快照，再退到脚本内置映射表；
  - 报告最下方"代码清单"仅保留沪深主板(60/000/001/002/003)，剔除 ST/科创板(688)/
    创业板(300,301)/北交所(8,920,430)/港股(.HK)，方便直接复制；
  - 报告输出目录：<程序目录>/个股利好报告/YYYYMMDD_个股利好细化报告.md
  - 历史记录：<程序目录>/个股利好报告/历史提取记录.jsonl
  - 代码表缓存：<程序目录>/个股利好报告/股票代码表.json
  - 回补缓存：<程序目录>/个股利好报告/_回补缓存/YYYYMMDD.json（规则回测的数据源）
  - 行情缓存：<程序目录>/个股利好报告/_行情缓存/<symbol>.json（按自然日复用，避免重复请求）
"""
import argparse
import codecs
import concurrent.futures
import datetime
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 编解码器预热（打包成 exe 后必需）：
# socket.getaddrinfo 解析域名时会即时查找 "idna" 编解码器，而该模块是首次使用时才导入的。
# 多源并行抓取时 5 个线程会同时首次触发导入，存在竞争 —— 抢输的线程会抛
# LookupError: unknown encoding: idna，导致该源整批抓取失败（同一份 exe 时好时坏）。
# 这里在主线程、任何工作线程启动之前先查找一遍，把编解码器注册好，彻底消除该竞争。
for _enc in ("idna", "gbk", "gb18030", "utf-8"):
    try:
        codecs.lookup(_enc)
    except LookupError:
        pass
del _enc


def writable_dir():
    """可写目录：打包成 exe 后为 exe 所在目录，否则为脚本所在目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name):
    """只读资源：打包后优先取解包目录(_MEIPASS)，否则取脚本目录。"""
    base = getattr(sys, "_MEIPASS", None) or writable_dir()
    return os.path.join(base, name)


BASE_DIR = writable_dir()
REPORT_DIR = os.path.join(BASE_DIR, "个股利好报告")
HISTORY_FILE = os.path.join(REPORT_DIR, "历史提取记录.jsonl")
STOCK_TABLE_CACHE = os.path.join(REPORT_DIR, "股票代码表.json")
BACKFILL_DIR = os.path.join(REPORT_DIR, "_回补缓存")    # 回补模式下逐日结构化结果
QUOTE_DIR = os.path.join(REPORT_DIR, "_行情缓存")       # 按交易日缓存的新浪行情
STOCK_TABLE_SNAPSHOT = "股票代码表_快照.json"
STOCK_TABLE_MAX_AGE_DAYS = 30
TASK_NAME = "个股利好提取器"
VERSION = "2.4"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# ============================= 股票代码映射表 =============================
# 名称 -> (代码, 市场)   市场: 'HS'沪深主板 / 'CY'创业板 / 'KCB'科创板 / 'BJ'北交所 / 'HK'港股
STOCK_MAP = {
    "亿纬锂能": ("300014", "CY"), "赛意信息": ("300687", "CY"), "宝通科技": ("300031", "CY"),
    "顺丰控股": ("002352", "HS"), "顺丰同城": ("09699", "HK"), "中通快递": ("02057", "HK"),
    "神威药业": ("02877", "HK"), "宁德时代": ("300750", "CY"), "神火股份": ("000933", "HS"),
    "爱旭股份": ("600732", "HS"), "东方国信": ("300166", "CY"), "长飞光纤": ("601869", "HS"),
    "华谊集团": ("600623", "HS"), "江化微": ("603078", "HS"), "国泰海通": ("601211", "HS"),
    "金刚光伏": ("300093", "CY"), "拓荆科技": ("688072", "KCB"), "神州数码": ("000034", "HS"),
    "欧菲光": ("002456", "HS"), "三孚新科": ("688359", "KCB"), "路维光电": ("688401", "KCB"),
    "天赐材料": ("002709", "HS"), "协鑫能科": ("002015", "HS"), "禾川科技": ("688320", "KCB"),
    "游族网络": ("002174", "HS"), "康达新材": ("002669", "HS"), "石药集团": ("01093", "HK"),
    "广汽集团": ("601238", "HS"), "小鹏汽车": ("09868", "HK"), "赛力斯": ("601127", "HS"),
    "正裕工业": ("603089", "HS"), "恒勃股份": ("301225", "CY"), "五洋自控": ("300420", "CY"),
    "利尔达": ("920249", "BJ"), "天宇股份": ("300702", "CY"), "东阳光": ("600673", "HS"),
    "白云山": ("600332", "HS"), "祥鑫科技": ("002965", "HS"), "光环新网": ("300383", "CY"),
    "小米集团": ("01810", "HK"), "商汤科技": ("00020", "HK"), "中煤能源": ("601898", "HS"),
    "百联股份": ("600827", "HS"), "上汽集团": ("600104", "HS"), "春秋航空": ("601021", "HS"),
    "国药一致": ("000028", "HS"), "中际旭创": ("300308", "CY"), "阿里巴巴": ("09988", "HK"),
    "拓普集团": ("601689", "HS"), "三花智控": ("002050", "HS"), "浙江荣泰": ("603119", "HS"),
    "新泉股份": ("603179", "HS"), "均胜电子": ("600699", "HS"), "智己汽车": ("600104", "HS"),
    "高域科技": ("601238", "HS"), "协鑫光电": ("002015", "HS"),
    "贵州茅台": ("600519", "HS"), "五粮液": ("000858", "HS"), "中国平安": ("601318", "HS"),
    "招商银行": ("600036", "HS"), "平安银行": ("000001", "HS"), "恒瑞医药": ("600276", "HS"),
    "东方财富": ("300059", "CY"), "中信证券": ("600030", "HS"), "紫金矿业": ("601899", "HS"),
    "长江电力": ("600900", "HS"), "伊利股份": ("600887", "HS"), "比亚迪": ("002594", "HS"),
    "隆基绿能": ("601012", "HS"), "通威股份": ("600438", "HS"), "中国电信": ("601728", "HS"),
    "中国移动": ("600941", "HS"), "中国神华": ("601088", "HS"), "中国石油": ("601857", "HS"),
    "中国石化": ("600028", "HS"), "中国中免": ("601888", "HS"), "三一重工": ("600031", "HS"),
    "美的集团": ("000333", "HS"), "格力电器": ("000651", "HS"), "海康威视": ("002415", "HS"),
    "海螺水泥": ("600585", "HS"), "中国建筑": ("601668", "HS"), "中国中铁": ("601390", "HS"),
    "山西汾酒": ("600809", "HS"), "泸州老窖": ("000568", "HS"), "立讯精密": ("002475", "HS"),
    "万华化学": ("600309", "HS"), "中国中车": ("601766", "HS"), "东方电气": ("600875", "HS"),
    "厚普股份": ("300471", "CY"), "茅台": ("600519", "HS"),
}

# ============================= 利好分类关键词 =============================
CATEGORIES = [
    ("订单/合同", ["合同", "中标", "订单", "供货", "签署", "签订", "签约", "框架协议", "采购协议",
                   "长期协议", "供货协议", "合作协议", "斩获", "揽得", "拿下"]),
    ("增持/回购/分红", ["增持", "回购", "特别股息", "派发", "派息", "分红", "每股派", "现金红利"]),
    ("扩产/投资", ["投建", "新建", "扩产", "产能", "定增", "增资", "收购", "入股", "开工建设",
                   "投资建设", "投产", "达产", "竣工"]),
    ("技术/产品突破", ["量产", "交付", "获批", "批件", "突破", "认证", "上线", "发布", "小批量",
                       "验证通过", "打通", "首发", "出货", "下线"]),
    ("合作/合资/融资", ["战略合作", "合资", "合营", "融资", "A轮", "B轮", "完成融资", "共同投资",
                        "设立", "新设"]),
    ("经营改善", ["门店", "航线", "增长", "回升", "恢复", "创新高", "稳中向好", "回暖", "预增", "扭亏"]),
    # 单字"或"已改为"或将"：原写法会把"或者""或将于"等无关表述误判为传闻类
    ("预期催化/传闻", ["传闻", "网传", "据悉", "消息称", "审厂", "拟", "有望", "或将", "意向", "接洽"]),
]

# 「签订/签署/合同/签约」在政策问答、宏观报道里同样是常用动词，本身不证明个股拿到订单；
# 只有同时出现实词（订单/中标/供货…）或金额时，才承认是『订单/合同』。
# 反例（30 日实测）：财政部"居民购房贷款贴息政策答记者问"里的
# "只需在签订贷款合同时，同步授权银行代为办理贴息" → 该条曾把整条政策问答定成 L5 订单落地。
ORDER_STRONG = ("订单", "中标", "供货", "采购", "框架协议", "长期协议", "供货协议",
                "采购协议", "斩获", "揽得", "拿下")
ORDER_AMOUNT_PAT = re.compile(r"\d[\d,.]*\s*(?:亿|万)?\s*元")

# 宏观政策问答/解读类文案：主体是部委政策而非某家上市公司，不作为个股利好来源。
MACRO_POLICY_PAT = re.compile(r"答记者问|答问实录|政策问答|政策解读|有关负责人就")

# 盘面异动播报 / 热点汇总类文案：标题形如"XX概念震荡走高 YY涨停"，个股只是被点名的
# 涨跌名单（正文"消息面上"多是行业政策、研报观点或别人家的事件），不是该股自己的利好。
# 30 日实测 53 条，如"【电力板块逆势活跃 浙江新能涨停】""【今日投资舆情热点】1）机器人：特斯拉…"。
# 只认标题（开头【…】）形态，避免误伤正文里出现"概念/涨停"的真公告。
BOARD_MOVE_PAT = re.compile(
    # ① 盘面异动播报："XX概念/板块震荡走高 YY涨停/连板/领涨"
    r"^【[^】]{0,40}(?:概念|板块|题材)[^】]{0,24}(?:涨停|连板|拉升|活跃|走强|走高|走低|反弹|回升"
    r"|高开|低开|异动|涨超|领涨|领跌|强势|涨幅居前|跌幅居前)"
    # ② 热点汇总列表："今日投资舆情热点""涨停复盘"
    r"|^【[^】]{0,24}(?:舆情热点|热点前瞻|涨停复盘|热点追踪|市场热点|题材热点|盘中异动|盘面异动|热点解读)】"
    # ③ 大盘/资金综述："A股午评…""主力资金：…净流出超299亿"
    r"|^【[^】]{0,12}(?:A股)?(?:午评|收评|早盘播报|收盘播报|盘面综述|主力资金|资金流向|资金面)"
    # ④ 概念股综述："海外龙头开启涨价模式 融资加仓MLCC概念股""XX概念股受关注"
    r"|^【[^】]{0,40}(?:概念股|题材股|板块股)")

# ======================== 利好五级评级 & 两层级跟踪 ========================
# 层级：『订单落地』事件已确认（可计入业绩/股东回报）；『概念发酵』预期型、主题型，兑现不确定。
# BASE_LEVEL 为各类别的基础 (评级, 层级)，再由"落地词 / 未证实词 / 弱动作词"修正。
BASE_LEVEL = {
    "订单/合同": (5, "订单落地"),          # 硬利好：签署/中标即落地
    "增持/回购/分红": (5, "订单落地"),      # 硬利好：实施/预案确定即落地
    "技术/产品突破": (4, "订单落地"),       # 准硬：量产/交付/获批；仅发布/上线另行降级
    "扩产/投资": (3, "概念发酵"),           # 强催化：资本开支兑现周期长
    "合作/合资/融资": (2, "概念发酵"),      # 软利好
    "经营改善": (2, "概念发酵"),            # 软利好
    "预期催化/传闻": (1, "概念发酵"),       # 传闻预期
}
LEVEL_NAME = {5: "L5 硬利好", 4: "L4 准硬利好", 3: "L3 强催化", 2: "L2 软利好", 1: "L1 传闻预期"}
TIER_LANDED = "订单落地"
TIER_CONCEPT = "概念发酵"

# 已落地动作词（事件确认发生）
LANDING_WORDS = ["签署", "签订", "签约", "中标", "斩获", "揽得", "拿下", "收到", "获得",
                 "确认", "完成", "已实施", "实施回购", "已回购", "已增持", "落地",
                 "量产", "交付", "获批", "取得批件", "投产", "达产", "竣工", "出货",
                 "现金分红", "派发", "过户", "交割完成", "完成交割", "已交割", "成交",
                 "打入供应商", "成为供应商"]
LANDING_PATTERNS = [r"获.{0,12}(增持|回购|订单|合同|中标|定点)", r"中标.{0,20}(项目|合同|订单)"]
# 未证实/计划态词（概念发酵信号）
RUMOR_WORDS = ["传闻", "网传", "据悉", "消息称", "有消息", "市场消息", "拟", "有望", "或将",
               "或达", "或超", "计划", "预计", "意向", "探讨", "接洽", "考虑", "酝酿"]
# 技术类中仅属"发布/展示"而非量产交付的弱动作 -> 降级为概念发酵
SOFT_TECH_WORDS = ["发布", "上线", "亮相", "展出", "首发", "推出", "开启预约", "开启预售"]

# ======================== 利空分类（三级警示） ========================
# 严重程度：N3 重大利空（立案/退市/冻结/实控人） > N2 实质利空（减持/处罚/暴雷） > N1 软利空。
# 同一事件命中多个类别时取最严重（max）。
NEG_CATEGORIES = [
    ("立案/调查/被查", ["立案调查", "被立案", "立案侦查", "立案告知", "被查", "接受调查", "接受问询",
                       "被调查", "被传唤", "配合调查", "刑事立案", "涉嫌"]),
    ("处罚/监管措施", ["被罚", "罚款", "处罚", "没收违法所得", "监管函", "警示函", "监管措施",
                       "公开谴责", "通报批评", "责令改正", "问询函", "监管工作函", "关注函",
                       "信披违规", "违规担保", "违规占用"]),
    ("风险警示/ST/*ST", ["被ST", "退市风险警示", "撤销退市风险", "触及退市", "退市风险",
                         "财务造假", "审计非标", "无法表示意见", "保留意见"]),
    ("减持/抛售", ["减持", "清仓式减持", "套现", "拟清仓", "被动减持"]),
    ("冻结/司法/担保", ["股权被冻结", "股份被冻结", "司法冻结", "被查封", "被拍卖", "被强制执行",
                        "连带担保责任", "担保涉诉", "质押爆仓"]),
    ("业绩/亏损/商誉", ["巨亏", "大幅亏损", "商誉减值", "资产减值", "计提减值", "业绩暴雷",
                        "业绩下修", "业绩预亏", "亏损扩大", "由盈转亏", "净利润亏损",
                        "连续亏损", "业绩预告向下修正"]),
    ("经营/合作终止", ["终止合作", "终止协议", "解除合同", "停止合作", "召回", "产品缺陷",
                       "质量问题", "安全事故", "停产停业"]),
    ("高管/实控人变动（负面）", ["实控人被查", "董事长被查", "董秘被查", "高管被立案",
                                "董事长辞任", "董秘辞职", "实控人失联", "实控人被拘留"]),
    ("澄清/辟谣", ["辟谣", "澄清不实", "纯属捏造", "主观臆测", "严正声明", "与事实不符", "传闻不实",
                   "澄清并致歉", "公告更正", "信披失误", "修订痕迹"]),
]
NEG_LEVEL = {"立案/调查/被查": 3, "处罚/监管措施": 2, "风险警示/ST/*ST": 3, "减持/抛售": 2,
             "冻结/司法/担保": 2, "业绩/亏损/商誉": 2, "经营/合作终止": 2,
             "高管/实控人变动（负面）": 3, "澄清/辟谣": 1}
NEG_LEVEL_NAME = {1: "N1 软利空", 2: "N2 实质利空", 3: "N3 重大利空"}
# "终止减持/承诺不减持"实为利好侧事件，不能算利空
NEG_TERMINATED = ("终止减持", "提前终止减持", "未减持", "不减持", "放弃减持", "取消减持")
# 否定式表述同样不是利空，典型样板文：
# "【9月29日增减持汇总】…包括彤程新材、海南高速、中国汽研在内的3家A股上市公司披露拟增持情况，
#   当日暂无A股上市公司披露拟减持情况" —— 整条其实只有增持，却因"减持"二字被判成减持利空。
# 否定词必须紧邻"减持"且不跨句，避免"未来三年将减持"这类真减持被误剔除（故不收录单个"未""无"）。
NEG_DENIED_PAT = re.compile(
    r"(?:暂无|没有|不存在|并未|未曾|未有|均未|不涉及|不再|不会|未获|未出现|无股东|无公司|无上市)"
    r"[^。；，]{0,12}?减持")
# "解除冻结/撤销冻结"是风险出清（偏中性偏利好），与"终止减持"同理不能算利空。
# 30 日回测：该类 4 条平均超额 +0.66%、下跌命中率仅 25.0%，而真·被冻结 13 条为
# -0.21%/53.8% —— 两者混在一起会把冻结类整体表现拉偏。
# 只用「解除类动词 + 冻结」紧邻搭配，避免把"冻结"文中别的"解除"误当成解冻。
NEG_RELEASE_PAT = re.compile(r"(?:解除|撤销|取消|终止)[^。；，]{0,8}?(?:司法|轮候)?冻结")
# 利空侧不纳入的泛情绪词（太宽泛，且通常伴随具体利空事件才进明细）
EXCLUDE_FOR_NEGATIVE = ["暴跌", "大跌", "大幅下滑", "业绩下滑", "风险提示"]

# 主题词 -> 主线名（用于主线归纳）
THEMES = [
    ("AI算力", ["AI", "算力", "智算", "大模型", "超节点", "昇腾", "GPU", "CPO", "光模块", "液冷"]),
    ("机器人与具身智能", ["机器人", "具身", "人形", "灵巧手", "机械臂", "Optimus"]),
    ("半导体/先进封装", ["半导体", "芯片", "晶圆", "封装", "掩膜版", "光刻", "NAND", "存储", "CoWoS"]),
    ("新能源", ["锂", "电池", "钙钛矿", "光伏", "储能", "氢能", "风电", "钠电", "换电", "充电"]),
    ("医药/医疗", ["医药", "创新药", "CDMO", "医疗", "药", "诊断", "疫苗", "基因", "脑机"]),
    ("汽车/智能驾驶", ["汽车", "整车", "智驾", "Robotaxi", "飞行汽车", "自动驾驶", "混动", "问界"]),
    ("低空/商业航天", ["低空", "飞行", "火箭", "卫星", "航天", "适航", "星舰"]),
    ("贵金属/有色", ["黄金", "白银", "铜", "钯", "铂", "锂", "稀土", "有色"]),
    ("股东回报", ["增持", "回购", "股息", "分红", "派息"]),
    ("国企改革/资本运作", ["收购", "并购", "国资", "实控人", "重组", "过户"]),
]

# 利好侧安全网：出现即不计入利好（利空侧另有 NEG_CATEGORIES 做分级归类）
# 注意：本表不含"减持" —— 该词已由 classify_negative 按语境判断（"承诺不减持""暂无…拟减持"不是利空），
# 若在此再拦一刀，"披露拟增持情况，当日暂无A股上市公司披露拟减持情况"这类汇总增持也会被一起丢掉。
EXCLUDE_KEYWORDS = ["终止", "召回", "延期", "延迟", "亏损", "被查", "调查", "警示", "处罚",
                    "违规", "立案", "冻结", "辞任", "辞职", "离任", "卸任", "停牌", "收监管函"]
# 硬垃圾词：ST 状态 / 退市 / 停牌等，既不适合进利好也不适合进利空明细
EXCLUDE_FOR_POSITIVE = ["*ST", "退市", "停牌", "复牌", "爆雷", "违约"]
# ST 状态词用正则限定边界，避免把 POST / FAST 这类英文单词里的 "ST" 误判成风险警示股
ST_TAG_RE = re.compile(r"(?<![A-Za-z])ST(?![a-z])")

# 同时是通用中文词汇的股票简称：单独出现时极易误配（如"新产业"命中"新兴产业"、
# "老百姓"命中"老百姓关心的问题"），必须位于标题头部或紧邻公司/公告类标记才认定为个股。
# 全量代码表带来召回率大幅提升的同时也会引入这类噪声，可按需继续补充。
AMBIGUOUS_NAMES = {
    "农产品", "老百姓", "机器人", "新产业", "线上线下", "探路者", "太平洋", "张家界",
    "陆家嘴", "金融街", "中关村", "太阳能", "大智慧", "步步高", "向日葵", "数字人",
    "数据港", "王府井", "外高桥", "全聚德", "好想你", "好当家", "好太太", "家家悦",
    "人民网", "新华网", "三人行", "天下秀", "新世界", "新大陆", "新希望", "新城市",
    "新天地", "三棵树", "红太阳", "大西洋", "白云山", "连云港", "徐家汇", "张家港",
    "西大门", "石榴", "光明", "大众", "东方", "中国", "恒大", "利群", "三毛", "大商",
}
# 通用词型名称的采信词头：只要"紧跟冒号/公告词"，或"名称+股份/集团"这类公司名写法。
# 刻意不含裸"公司"（"杭州机器人公司增资250倍"）、裸"上市/披露"这类弱证据。
AMB_STRONG_CONTEXT = ("：", ":", "公告", "股份", "集团")   # "有限公司"另做同名不同司的判断


def _strong_context(text, idx, length, table):
    """通用词型名称（老百姓/机器人/太阳能…）的采信证据，必须是"看着就在指这家公司"的形式证据：
    1) 紧跟冒号或公告/公司类词头（"老百姓：""王府井公告""连云港股份"）；
    2) 处于"、"分隔的个股并列清单中（顿号后必须紧跟另一只个股简称）。
    刻意不再采信"位于句首/标点前"和"前文出现公告/收购"这两类弱证据——
    30 日实测：财政部"居民购房贷款贴息政策答记者问"里
    「……让流程"高效办"。老百姓要省心，组织实施就得顺畅」正是靠"句号前"这条漏洞，
    把普通名词"老百姓"挂到了 603883 头上；同因误挂的还有"人形机器人""连云港海事局"
    "大西洋成品油船运价""太阳能发电"等（30 天内通用词名命中 28 条，误配占多数）。"""
    tail = text[idx + length: idx + length + 8]
    if tail.startswith("、"):        # 顿号并列：后面必须紧跟另一只个股
        return any(tail[1:1 + n] in table for n in (2, 3, 4))
    if tail.startswith("有限公司"):
        # "杭州宇树机器人有限公司"——前一字还是汉字，说明这是名字更长的另一家公司
        # （宇树科技旗下主体，非 300024 机器人），不算本股。
        return idx == 0 or not ("\u4e00" <= text[idx - 1] <= "\u9fa5")
    return any(tail.startswith(m) for m in AMB_STRONG_CONTEXT)


# 券商/机构/信息平台类个股：它们常以"发布方"身份出现在快讯里（研报观点、行业解读），
# 这类消息的利好主体是正文提到的产业链公司，而不是发布观点的机构本身。
# 例："中信建投：看好人形机器人产业链"该计入机器人链公司，不该计入中信建投。
# 注意：只有处于"发布观点"语境时才剔除；若它们自己发公告（如"XX：关于回购的公告"）仍保留。
SOURCE_ORGS = {
    "中信建投", "中信证券", "招商证券", "华泰证券", "国泰海通", "中金公司", "广发证券",
    "兴业证券", "申万宏源", "东吴证券", "天风证券", "国信证券", "长江证券", "国金证券",
    "方正证券", "浙商证券", "财通证券", "东方证券", "光大证券", "中国银河", "太平洋证券",
    "中泰证券", "西部证券", "中银证券", "华西证券", "东北证券", "国海证券", "东兴证券",
    "第一创业", "红塔证券", "南京证券", "华安证券", "山西证券", "长城证券", "信达证券",
    "首创证券", "财达证券", "华鑫股份", "华林证券", "国联民生", "湘财股份", "哈投股份",
    "锦龙股份", "同花顺", "东方财富", "大智慧", "指南针", "国投资本", "华创云信",
}
# "观点"标志词：出现在机构名之后，说明该机构是在发表看法而非被利好
OPINION_HINTS = ("认为", "指出", "表示", "称", "预计", "看好", "建议", "维持", "点评", "分析",
                 "研判", "展望", "研报", "策略", "观点", "解读", "预测", "上调", "下调",
                 "评级", "目标价", "调研", "报告", "发布")
# 研报特征词：出现在全文里，说明这是一条券商观点/研报类消息（标题式"机构名：观点"用它兜底）
REPORT_WORDS = ("研报", "认为", "指出", "点评", "策略", "看好", "测算", "分析称", "评级", "目标价")
# "机构名：" 之后若是自身事项（公告/中标/回购/被立案…），仍属该机构自己的消息，要保留；
# 否则视为快讯发布方，不计入个股主体（避免把"中信证券：观点/快讯"标成利好或利空主体）。
ANNOUNCE_HEADS = ("关于", "公告", "回购", "增持", "减持", "中标", "签订", "签署", "签约",
                  "合同", "订单", "获", "拟", "被", "立案", "收到", "澄清", "说明", "终止")


# 机构观点条的识别词：标题"【机构：…】"里出现这些，说明是研报观点/行业点评，
# 正文点到的个股只是观点标的（甚至只是举例），不是事件主体。
ORG_VIEW_WORDS = ("研报", "评级", "目标价", "维持", "上调", "下调", "首予", "首次覆盖",
                  "覆盖", "看好", "推荐", "指出", "认为", "点评", "分析", "拐点", "展望",
                  "预计", "策略", "建议")


def is_org_view_item(text):
    """整条是不是『机构观点/研报条』。
    形态：标题以券商/机构名+冒号开头（【中信建投：医疗器械板块拐点来临】），
    且标题或正文带研报观点词；该机构自身事项（"中信证券：关于回购股份的公告"）不算。
    这类条目里被提及的个股按"预期型"处理：降一级、层级固定『概念发酵』。"""
    m = re.match(r"^【([^】：:]{2,10})[：:]", text)
    if not m or m.group(1) not in SOURCE_ORGS:
        return False
    head = text[:60]
    return any(w in head for w in ORG_VIEW_WORDS) or any(w in text for w in ("研报", "评级", "目标价"))


def _is_news_source(text, idx, length):
    """判断该名称是否为"消息发布方"（券商研报/机构观点），是则不作为个股主体。
    典型：中信建投：智谱商业化提速…【中信建投研报指出…】——主体应是正文提到的公司。
    判定：① 名称后紧跟冒号且随后是观点性表述，或全文带研报特征词（标题式观点）；
         ② 名称后紧跟"研报/发布/认为"等发布类动词（含"华泰证券港股策略研报称"这类写法）；
         ③ 名称后紧跟冒号且其后不是自身事项（公告/中标/被立案…），按快讯发布方处理。"""
    tail = text[idx + length: idx + length + 18]
    if not tail:
        return False
    if tail[0] in "：:" and any(w in tail[1:16] for w in OPINION_HINTS):
        return True
    if any(w in text for w in REPORT_WORDS):
        # 全文带研报特征词：这条消息整体是券商观点/研报类，机构名只是出处
        return True
    if tail[0] in "：:":
        # 冒号后是自身事项说明（如"中信证券：关于回购股份的公告"）时保留，
        # 否则视为快讯/栏目名（如"中信证券：11月金股组合"），不计入个股主体。
        return not any(tail[1:].lstrip().startswith(h) for h in ANNOUNCE_HEADS)
    return any(w in tail[:8] for w in ("研报", "发布", "认为", "指出", "表示", "称", "预计",
                                       "看好", "建议", "点评", "分析", "策略", "评论"))


def http_get(url, timeout=15, referer="https://www.baidu.com/"):
    """标准库抓取，返回响应文本；失败抛异常。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*",
                                               "Referer": referer})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    for enc in ("utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def to_time_str(value):
    """把 unix 时间戳(秒/毫秒)或时间字符串统一成 'YYYY-MM-DD HH:MM:SS'，无法识别时返回原串。"""
    s = str(value or "").strip()
    if not s:
        return ""
    if re.fullmatch(r"\d{10,13}", s):
        ts = int(s)
        if ts > 10 ** 11:
            ts //= 1000
        try:
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, ValueError, OverflowError):
            return ""
    return s


def parse_time(value):
    """把消息时间解析成 datetime；失败返回 None。"""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


# ============================= 时间窗口与回溯 =============================
# 快讯源大多只提供"最新一页"，要靠翻页/游标才能回溯到指定日期。
MAX_HISTORY_DAYS = 10       # 快讯源最多回溯天数（再往前页数爆炸，不做）
# 巨潮公告是官方历史存档：seDate 直接按日期区间查，不靠翻页回溯，任意历史日期都能查，
# 故 30 日回补以它为主力；超过 MAX_HISTORY_DAYS 的日期只启用该源。
MAX_HISTORY_DAYS_CNINFO = 30
CNINFO_SOURCE_NAME = "巨潮公告"
PAGE_CAP = 500              # 单源单次最大翻页次数（安全阀，防止接口异常时死循环）


def in_window(t, start, end):
    """消息时间是否落在 [start, end) 窗口内；时间无法解析的一律丢弃。"""
    dt = parse_time(t)
    return dt is not None and start <= dt < end


def _norm_key(text):
    """去重键：压缩空白后取前 80 字。"""
    return re.sub(r"\s+", "", text or "")[:80]


def _min_dt(times):
    """一组时间字符串里最早的那个 datetime（无法解析的忽略），空则 None。"""
    ds = [d for d in (parse_time(t) for t in times) if d is not None]
    return min(ds) if ds else None


def fetch_em(start, end, max_pages=1):
    """东方财富 7x24 快讯。
    注意：实测该接口返回中不含 sortEnd 游标字段，传空/传值结果完全相同，
    即无法翻页回溯，只能取到最新一页（约 3 小时）。
    因此历史日期模式下该源会被标注为『不支持历史』，不参与回溯。
    """
    url = ("https://np-listapi.eastmoney.com/comm/web/getFastNewsList?client=web"
           "&biz=web_724&fastColumn=102&sortEnd=&pageSize=100&req_trace=")
    data = json.loads(http_get(url))
    items = (data.get("data") or {}).get("fastNewsList") or []
    out = []
    for it in items:
        t = to_time_str(it.get("showTime"))
        body = ((it.get("title") or "").strip() + " " + (it.get("summary") or "").strip()).strip()
        if body and in_window(t, start, end):
            out.append({"time": t, "text": body, "source": "东方财富"})
    return out


def fetch_sina(start, end, max_pages=PAGE_CAP):
    """新浪财经 7x24 直播：page 翻页可回溯历史（实测每页约 100 条 / 1 小时）。
    注意：实测 page>100 起返回内容不再变化（固定为第 100 页那批，最早约到 6 天前），
    故加"无进展即停"保护，避免空翻数百页。
    """
    out, seen, prev_oldest = [], set(), None
    for page in range(1, max_pages + 1):
        url = (f"https://zhibo.sina.com.cn/api/zhibo/feed?page={page}&page_size=100"
               "&zhibo_id=152&tag_id=0&dire=f&dpc=1")
        data = json.loads(http_get(url))
        items = (data.get("result", {}).get("data", {}).get("feed", {}).get("list")) or []
        if not items:
            break
        for it in items:
            t = to_time_str(it.get("create_time"))
            if not in_window(t, start, end):
                continue
            body = html.unescape(re.sub(r"<[^>]+>", "", it.get("rich_text") or "")).strip()
            if not body:
                continue
            key = _norm_key(body)
            if key in seen:
                continue
            seen.add(key)
            out.append({"time": t, "text": body, "source": "新浪财经"})
        oldest = _min_dt([to_time_str(i.get("create_time")) for i in items])
        if oldest is None or oldest < start:
            break       # 已翻过窗口起点，停止翻页
        if prev_oldest is not None and oldest >= prev_oldest:
            break       # 页面不再往前推进（已达该接口翻页上限），停止
        prev_oldest = oldest
    return out


def fetch_wallstcn(start, end, max_pages=PAGE_CAP):
    """华尔街见闻 7x24 快讯：cursor 翻页可回溯（实测每页约 100 条 / 3.5 小时）。"""
    out, seen, cursor = [], set(), None
    for _ in range(max_pages):
        url = "https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&limit=100"
        if cursor:
            url += f"&cursor={cursor}"
        data = json.loads(http_get(url))
        dd = data.get("data") or {}
        items = dd.get("items") or []
        if not items:
            break
        for it in items:
            t = to_time_str(it.get("display_time"))
            if not in_window(t, start, end):
                continue
            body = re.sub(r"<[^>]+>", "", it.get("content_text") or it.get("content") or "").strip()
            if not body:
                continue
            key = _norm_key(body)
            if key in seen:
                continue
            seen.add(key)
            out.append({"time": t, "text": body, "source": "华尔街见闻"})
        oldest = _min_dt([to_time_str(i.get("display_time")) for i in items])
        nxt = dd.get("next_cursor")
        if oldest is not None and oldest < start:
            break
        if not nxt or nxt == cursor:
            break       # 游标不再前进，防止死循环
        cursor = nxt
    return out


def _cls_sign(params):
    """财联社接口签名：md5(sha1(按key排序的query))。"""
    raw = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hashlib.md5(hashlib.sha1(raw.encode("utf-8")).hexdigest().encode("utf-8")).hexdigest()


def fetch_cls(start, end, max_pages=PAGE_CAP):
    """财联社电报（需签名）：last_time 传上一批最早时间戳可回溯（实测每轮约 50 条 / 1.5 小时）。"""
    out, seen, last_time = [], set(), ""
    for _ in range(max_pages):
        params = {"app": "CailianpressWeb", "category": "", "last_time": str(last_time),
                  "os": "web", "refresh_type": "1", "rn": "50", "sv": "8.4.6"}
        params["sign"] = _cls_sign({k: v for k, v in params.items() if k != "sign"})
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = "https://www.cls.cn/v1/roll/get_roll_list?" + query
        data = json.loads(http_get(url, referer="https://www.cls.cn/telegraph"))
        if str(data.get("errno")) not in ("0", "None"):
            raise RuntimeError(f"财联社接口返回错误：{data.get('msg') or data.get('errno')}")
        items = (data.get("data") or {}).get("roll_data") or []
        if not items:
            break
        nxt = 0
        for it in items:
            t = to_time_str(it.get("ctime"))
            try:
                cts = int(it.get("ctime") or 0)
            except (TypeError, ValueError):
                cts = 0
            if cts and (not nxt or cts < nxt):
                nxt = cts
            if not in_window(t, start, end):
                continue
            body = re.sub(r"<[^>]+>", "", it.get("content") or it.get("title") or "").strip()
            if not body:
                continue
            key = _norm_key(body)
            if key in seen:
                continue
            seen.add(key)
            out.append({"time": t, "text": body, "source": "财联社"})
        if not nxt or str(nxt) == str(last_time):
            break       # 时间戳不再前进，防止死循环
        last_time = nxt
        oldest = parse_time(to_time_str(nxt))
        if oldest is not None and oldest < start:
            break       # 已翻过窗口起点，停止翻页
    return out


# 巨潮资讯网：沪深北交易所指定的官方信息披露平台，公告权威性最高，
# 且每条公告自带"公司简称 + 代码"（交易所口径），主体绝不会识别错。
CNINFO_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
# 检索词分两组：利好侧沿用原 8 个高频词；利空侧补齐常见风险类公告标题词。
# 之所以要加利空侧：公告源原先只搜利好词，导致 30 日回补时利空样本几乎全部来自快讯源
# （而快讯源只能回溯 10 天），利空的 N3/N2/N1 分档根本无从校验。
CNINFO_KEYS_POS = ("中标", "合同", "回购", "增持", "获批", "签订", "订单", "投产")
CNINFO_KEYS_NEG = ("减持", "立案", "处罚", "问询函", "预亏", "诉讼", "质押", "冻结",
                   "退市风险", "终止")
CNINFO_KEYS = CNINFO_KEYS_POS + CNINFO_KEYS_NEG


def http_post(url, params, timeout=20, referer="http://www.cninfo.com.cn/"):
    """标准库表单 POST，返回响应文本；失败抛异常。"""
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": UA, "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded", "Referer": referer})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    for enc in ("utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def fetch_cninfo(start, end, max_pages=10):
    """巨潮公告：按利好类关键词检索公告标题，把"简称(代码)"前置进正文，
    既保留权威主体，又无需改动后续识别逻辑。
    seDate 直接按目标窗口取日期区间 —— 该库是官方历史存档，任意历史日期都能查，
    是唯一不受"只给最新一页"限制的源。
    """
    se = "%s~%s" % (start.strftime("%Y-%m-%d"),
                    (end - datetime.timedelta(seconds=1)).strftime("%Y-%m-%d"))
    out, seen = [], set()
    for kw in CNINFO_KEYS:
        for page in range(1, max_pages + 1):
            params = {"pageNum": str(page), "pageSize": "50", "column": "szse", "tabName": "fulltext",
                      "plate": "", "stock": "", "searchkey": kw, "secid": "", "category": "",
                      "trade": "", "seDate": se, "sortName": "", "sortType": "", "isHLtitle": "true"}
            try:
                data = json.loads(http_post(CNINFO_URL, params))
            except Exception:
                break
            anns = data.get("announcements") or []
            for a in anns:
                code = str(a.get("secCode") or "").strip()
                name = str(a.get("secName") or "").strip()
                title = re.sub(r"<[^>]+>", "", a.get("announcementTitle") or "").strip()
                if not code or not name or not title:
                    continue
                t = to_time_str(a.get("announcementTime"))
                if not in_window(t, start, end):
                    continue
                key = _norm_key(name + code + title)
                if key in seen:
                    continue
                seen.add(key)
                if title.startswith(name):     # 标题常以公司名开头，去掉与前置主体重复的部分
                    title = title[len(name):].lstrip("：: 　") or title
                out.append({"time": t, "text": f"{name}({code})：{title}", "source": "巨潮公告"})
            if len(anns) < 50:
                break
    return out


# (来源名, 抓取函数, 是否支持历史回溯)
FETCHERS = [("东方财富", fetch_em, False), ("新浪财经", fetch_sina, True),
            ("华尔街见闻", fetch_wallstcn, True), ("财联社", fetch_cls, True),
            ("巨潮公告", fetch_cninfo, True)]


def fetch_news(start, end, history=False, days_back=0):
    """多源并行抓取（限定 [start, end) 窗口），合并去重。返回 (消息列表, 成功来源, 失败来源)。
    history=True 时跳过不支持回溯的源并如实标注，绝不用"最新一页"冒充历史数据。
    days_back 超过 MAX_HISTORY_DAYS 时快讯源翻页成本爆炸，只保留巨潮公告（官方存档，按日直查）。
    各源独立翻页，故用线程池并行：历史日期回溯总耗时约等于最慢的那个源，而非各源之和。
    """
    all_news, ok, fail = [], [], []
    seen = set()

    # 回补较远的历史日期时（超过快讯源回溯上限），只有巨潮公告参与
    cninfo_only = history and days_back > MAX_HISTORY_DAYS

    def task_of(name, fn, sup):
        if not history:
            return name, fn, None
        if cninfo_only:
            # 只留巨潮公告；其余源（无论是否支持回溯）一律不参与，并如实标注原因
            if name == CNINFO_SOURCE_NAME:
                return name, fn, None
            return name, None, "回补仅取公告" if sup else "超出快讯回溯上限"
        return (name, None, "不支持历史") if not sup else (name, fn, None)

    tasks = [task_of(name, fn, sup) for name, fn, sup in FETCHERS]

    def worker(task):
        name, fn, skip = task
        if skip:
            return name, None, skip
        try:
            return name, fn(start, end), None
        except Exception as e:
            return name, None, f"({type(e).__name__})"

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(FETCHERS)) as ex:
        for name, items, err in ex.map(worker, tasks):        # ex.map 保序，输出稳定
            if err and not err.startswith("("):
                fail.append(f"{name}({err})")
            elif err:
                fail.append(name + err)
            elif items:
                ok.append(name)
                for it in items:
                    key = _norm_key(it["text"])
                    if key in seen:
                        continue
                    seen.add(key)
                    all_news.append(it)
            else:
                # 接口正常但窗口内没取到（如该源翻页上限已到），如实标注而非谎报成功
                fail.append(name + "(窗口内无数据)")
    return all_news, ok, fail


def is_main_board(code, market):
    """清单剔除规则：仅保留沪深主板；剔除 ST/科创板/创业板/北交所/港股。"""
    if market == "HK":
        return False
    if market == "KCB" or market == "CY" or market == "BJ":
        return False
    return bool(re.match(r"^(?:60\d{4}|00[0-3]\d{3})$", code))


def has_st_tag(text):
    """消息里是否出现 ST/*ST 风险警示标记（边界受限，不误伤英文单词里的 ST）。"""
    return bool(ST_TAG_RE.search(text)) or "*ST" in text


def is_st_name(name):
    """ST/*ST/退市股简称：明细与代码清单里一律剔除，避免把风险警示股当利好标的。"""
    n = (name or "").strip().upper().replace(" ", "")
    return n.startswith("ST") or n.startswith("*ST") or n.endswith("退")


# ============================= 行情取数（新浪，免 key） =============================
# 用途：给利好/利空明细标注「消息当日(T) / 次一交易日(T+1)」涨跌幅与相对基准指数的超额收益，
# 把"文本命中"升级为"文本命中 + 市场验证"，用真实市场反应反过来校准利好/利空分级。
#
# 接口（2026-09 本机实测可用；东方财富 push2/push2his 在本机被拒 RemoteDisconnected，勿用）：
#   * 日K  https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/
#           CN_MarketData.getKLineData?symbol=<sym>&scale=240&ma=no&datalen=N
#          返回 [{day, open, high, low, close, volume}]，沪/深/京/科创/创业板均可用；
#   * 快照 https://hq.sinajs.cn/list=sh600000,sz002456,bj920866（GBK），仅供盘中算当日 T0。
KLINE_URL = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
             "CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen={n}")
SNAPSHOT_URL = "https://hq.sinajs.cn/list={syms}"
QUOTE_REFERER = "https://finance.sina.com.cn/"
QUOTE_WORKERS = 8        # 行情并行线程数（新浪免 key，靠节流 + 重试控制压力）
QUOTE_RETRY = 2
KLINE_LEN = 45           # 日K根数：覆盖 30 日回补 + 缓冲
SNAPSHOT_BATCH = 800     # 单次快照请求的代码上限
BENCH_SSE = "sh000001"   # 沪市基准：上证指数
BENCH_SZE = "sz399106"   # 深/北基准：深证综指（sh000985 中证全指该接口返回陈旧数据，不可用）
ABNORMAL_PCT = 31.0      # 相邻收盘涨跌幅超过该值视为停牌复牌/除权失真，标为不可用

# 市场验证分档（按 T+1 相对基准的超额收益）
VERIFY_NONE = "待验证"
VERIFY_COLORS = {"强验证": "#c81e12", "弱验证": "#e0561f", "中性": "#6b7280",
                 "背离": "#2e7d32", "显著背离": "#0b6e4f", VERIFY_NONE: "#9ca3af"}


def sina_symbol(code, market=None):
    """股票代码 -> 新浪行情代码（沪 sh / 深 sz / 北交所 bj）；无法判定返回 None。"""
    code = (code or "").strip().upper()
    if not code.isdigit() or len(code) == 5:      # 港股(5位)不在行情范围内
        return None
    if code.startswith(("4", "8", "920")):
        return "bj" + code
    if code.startswith(("5", "6", "9")):          # 6xx 沪A / 5xx 基金 / 9xx 沪B
        return "sh" + code
    return "sz" + code


def bench_symbol(code):
    """个股对应的大盘基准：沪市用上证指数，深市/创业板/北交所用深证综指。"""
    code = (code or "").strip()
    if code.startswith(("60", "68", "9")) and not code.startswith("920"):
        return BENCH_SSE
    return BENCH_SZE


def parse_kline(data):
    """解析新浪日K返回的 JSON 数组为 {日期: 收盘}；非数组返回 None，脏行跳过。"""
    if not isinstance(data, list):
        return None
    out = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        day = str(row.get("day") or "")[:10]
        try:
            close = float(row.get("close"))
        except (TypeError, ValueError):
            continue
        if day:
            out[day] = close
    return out


def _quote_cache_path(symbol):
    return os.path.join(QUOTE_DIR, symbol + ".json")


def fetch_kline(symbol, datalen=KLINE_LEN, retry=QUOTE_RETRY):
    """取单只标的日K，返回 {日期 'YYYY-MM-DD': 收盘价}；多次失败返回 None。
    同一自然日内复用磁盘缓存：30 天回补时每只标的只需取一次，不必逐日重取。"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    try:
        with open(_quote_cache_path(symbol), encoding="utf-8") as f:
            c = json.load(f)
        if c.get("cache_day") == today and c.get("datalen") == datalen and c.get("data"):
            return c["data"]
    except Exception:
        pass
    url = KLINE_URL.format(sym=symbol, n=datalen)
    parsed = None
    for attempt in range(retry + 1):
        try:
            data = json.loads(http_get(url, timeout=15, referer=QUOTE_REFERER))
        except Exception:
            data = None
        parsed = parse_kline(data)
        if parsed is not None:
            break
        time.sleep(0.3 * (attempt + 1))
    # 只在 K 线不含当日（即当日未收盘的未完成K线）时落盘，避免把盘中半根K线缓存一整天
    if parsed and max(parsed) < today:
        try:
            os.makedirs(QUOTE_DIR, exist_ok=True)
            with open(_quote_cache_path(symbol), "w", encoding="utf-8") as f:
                json.dump({"cache_day": today, "datalen": datalen, "data": parsed}, f,
                          ensure_ascii=False)
        except Exception:
            pass
    return parsed


def parse_snapshot(text):
    """解析新浪快照返回文本为 {symbol: {name, prev, price, pct}}；
    字段不足 / 非数字 / 昨收或现价为 0 的坏行一律丢弃。"""
    out = {}
    for line in (text or "").splitlines():
        m = re.match(r'var hq_str_([A-Za-z0-9]+)="(.*)";', line.strip())
        if not m:
            continue
        cols = m.group(2).split(",")
        if len(cols) < 4:
            continue
        try:
            prev, price = float(cols[2]), float(cols[3])
        except ValueError:
            continue
        if not prev or not price:
            continue
        out[m.group(1)] = {"name": cols[0], "prev": prev, "price": price,
                           "pct": round((price - prev) / prev * 100, 2)}
    return out


def fetch_snapshot(symbols):
    """批量实时快照：返回 {symbol: {name, prev, price, pct}}；失败批次跳过。"""
    out = {}
    syms = [s for s in symbols if s]
    for i in range(0, len(syms), SNAPSHOT_BATCH):
        batch = syms[i:i + SNAPSHOT_BATCH]
        try:
            text = http_get(SNAPSHOT_URL.format(syms=",".join(batch)),
                            timeout=15, referer=QUOTE_REFERER)
        except Exception:
            continue
        out.update(parse_snapshot(text))
    return out


def build_quote_db(codes, verbose=True):
    """批量取行情日K：返回 {code: {"kline": {date: close}, "bench": {date: close}}}。
    单个标的失败只把 kline 置 None，绝不阻断报告生成。"""
    codes = sorted({c for c in codes if c})
    syms = {}
    for c in codes:
        s = sina_symbol(c)
        if s:
            syms[c] = s
    benches = sorted({bench_symbol(c) for c in codes})
    jobs = [("bench", b, b) for b in benches] + [("code", c, s) for c, s in syms.items()]
    if not jobs:
        return {}

    def worker(job):
        kind, key, sym = job
        return kind, key, fetch_kline(sym)

    got = {"bench": {}, "code": {}}
    fails = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=QUOTE_WORKERS) as ex:
        for kind, key, data in ex.map(worker, jobs):      # ex.map 保序，输出稳定
            if data is None:
                fails.append(key)
            else:
                got[kind][key] = data
    if verbose:
        print(f"[行情] 日K 成功 {len(got['code'])}/{len(syms)} 只，"
              f"基准 {len(got['bench'])}/{len(benches)} 个"
              + (f"，失败 {len(fails)} 个：{fails[:8]}" if fails else ""))
    db = {}
    for c in syms:
        db[c] = {"kline": got["code"].get(c), "bench": got["bench"].get(bench_symbol(c))}
    return db


def _pct_on(kline, day):
    """某交易日相对前一交易日收盘的涨跌幅 %；缺数据/首日/异常值返回 None。"""
    if not kline or day not in kline:
        return None
    days = sorted(kline)
    i = days.index(day)
    if i == 0:
        return None
    prev = kline[days[i - 1]]
    if not prev:
        return None
    pct = (kline[day] - prev) / prev * 100
    if abs(pct) > ABNORMAL_PCT:      # 停牌复牌 / 除权导致的失真值，不参与验证
        return None
    return round(pct, 2)


def _next_day(kline, day, limit=None):
    """day 之后的首个交易日；limit 给定时只接受严格早于 limit 的日期。"""
    if not kline:
        return None
    for d in sorted(kline):
        if d > day and (limit is None or d < limit):
            return d
    return None


def verify_label(exc):
    """按 T+1 相对基准超额收益给出市场验证标签。"""
    if exc is None:
        return VERIFY_NONE
    if exc >= 3.0:
        return "强验证"
    if exc >= 1.0:
        return "弱验证"
    if exc > -1.0:
        return "中性"
    if exc > -3.0:
        return "背离"
    return "显著背离"


def annotate_quotes(records, day_str, today_str, db, snapshot=None):
    """就地给 records 补行情字段：pct_t0 / pct_t1 / exc_t1 / verify。
    day_str 为消息所属交易日；T+1 只取"已收盘"的下一交易日（早于 today_str），未收盘标『待验证』。
    当日盘中在日K里还没有该日，T0 回退到实时快照现价。"""
    ok = 0
    for r in records:
        ent = db.get(r.get("code")) or {}
        kline, bench = ent.get("kline"), ent.get("bench")
        p0 = _pct_on(kline, day_str)
        if p0 is None and snapshot:
            snap = snapshot.get(sina_symbol(r.get("code")) or "")
            if snap:
                p0 = snap["pct"]
        nxt = _next_day(kline, day_str, limit=today_str) if kline else None
        p1 = _pct_on(kline, nxt) if nxt else None
        b1 = _pct_on(bench, nxt) if nxt else None
        exc = round(p1 - b1, 2) if (p1 is not None and b1 is not None) else None
        r["pct_t0"], r["pct_t1"], r["exc_t1"] = p0, p1, exc
        r["verify"] = verify_label(exc)
        if p0 is not None or p1 is not None:
            ok += 1
    return {"total": len(records), "quoted": ok}


def verify_agg(records, key_fn):
    """按 key_fn 分组统计 T+1 超额：返回 [(组名, 样本数, 平均超额%, 超额胜率%)]，按样本数降序。"""
    buckets = {}
    for r in records:
        exc = r.get("exc_t1")
        if exc is None:
            continue
        buckets.setdefault(key_fn(r), []).append(exc)
    out = []
    for key, vals in buckets.items():
        avg = sum(vals) / len(vals)
        win = sum(1 for v in vals if v > 0) / len(vals) * 100
        out.append((key, len(vals), round(avg, 2), round(win, 1)))
    return sorted(out, key=lambda x: (-x[1], x[0]))


def fmt_pct(v):
    """涨跌幅显示：None -> '—'，否则带符号两位小数。"""
    return "—" if v is None else f"{v:+.2f}%"


def quote_cell(r):
    """明细用的行情单元格文本。"""
    return (fmt_pct(r.get("pct_t0")), fmt_pct(r.get("pct_t1")),
            fmt_pct(r.get("exc_t1")), r.get("verify") or VERIFY_NONE)


def quote_selftest():
    """行情解析自测：注入缺失/零值/异常涨跌幅/脏行等坏样本，确认它们被识别为不可用，
    而不是被静默当成 0 或正常值。返回 (通过项数, 失败信息列表)。"""
    checks = []

    def chk(cond, msg):
        checks.append((bool(cond), msg))

    k = {"2026-09-08": 10.0, "2026-09-09": 10.5, "2026-09-10": 10.29, "2026-09-11": 10.5}
    chk(_pct_on(k, "2026-09-10") == -2.0, "正常涨跌幅计算错误")
    chk(_pct_on(k, "2026-09-08") is None, "首日缺前收，应返回 None")
    chk(_pct_on(k, "2026-12-31") is None, "缺失交易日应返回 None，不能当 0")
    chk(_pct_on({"2026-09-09": 0.0, "2026-09-10": 10.0}, "2026-09-10") is None,
        "前收为 0 应返回 None（防除零）")
    chk(_pct_on({"2026-09-09": 5.0, "2026-09-10": 20.0}, "2026-09-10") is None,
        f"相邻涨跌幅超 {ABNORMAL_PCT}% 应视为除权/停牌失真")
    chk(_next_day(k, "2026-09-10") == "2026-09-11", "下一交易日取错")
    chk(_next_day(k, "2026-09-10", limit="2026-09-11") is None, "limit 未收盘日应被排除")
    chk(_next_day(k, "2026-09-11") is None, "最后一日之后应无下一交易日")

    for exc, want in ((3.0, "强验证"), (2.99, "弱验证"), (1.0, "弱验证"), (0.99, "中性"),
                      (0.0, "中性"), (-0.99, "中性"), (-1.0, "背离"), (-3.0, "显著背离"),
                      (-100.0, "显著背离"), (None, VERIFY_NONE)):
        got = verify_label(exc)
        chk(got == want, f"验证分档 {exc} 应为 {want}，实为 {got}")

    for code, want in (("600000", "sh600000"), ("688050", "sh688050"), ("002456", "sz002456"),
                       ("300452", "sz300452"), ("000590", "sz000590"), ("920866", "bj920866"),
                       ("430139", "bj430139"), ("870508", "bj870508"), ("00700", None),
                       ("", None)):
        got = sina_symbol(code)
        chk(got == want, f"行情代码映射 {code!r} 应为 {want}，实为 {got}")
    for code, want in (("600000", BENCH_SSE), ("688050", BENCH_SSE), ("002456", BENCH_SZE),
                       ("300452", BENCH_SZE), ("920866", BENCH_SZE)):
        got = bench_symbol(code)
        chk(got == want, f"基准映射 {code} 应为 {want}，实为 {got}")

    # 日K脏行：非数组 / 缺日期 / 收盘非数字 / 行非字典，都必须跳过
    chk(parse_kline("oops") is None, "日K返回非数组应返回 None（触发重试）")
    chk(parse_kline([{"day": "2026-09-10", "close": "10.29"},
                     {"day": "2026-09-11"},
                     {"day": "", "close": "1"},
                     {"day": "2026-09-12", "close": "abc"},
                     "garbage"]
                    ) == {"2026-09-10": 10.29}, "日K脏行未被正确跳过")
    chk(parse_kline([]) == {}, "日K空数组应返回空字典（不是 None）")

    # 快照脏行：字段不足 / 非数字 / 昨收为 0，都必须丢弃
    snap = ('var hq_str_sh600000="浦发银行,0,10.00,10.20,0,0";\n'
            'var hq_str_sz002456="欧菲光,,,,";\n'
            'var hq_str_sz300452="山河药辅,0,0,0,0,0";\n'
            'var hq_str_bj920866="";\n'
            'garbage line\n')
    got = parse_snapshot(snap)
    chk(list(got) == ["sh600000"], f"快照坏行未被全部丢弃，实际保留 {list(got)}")
    chk(got.get("sh600000", {}).get("pct") == 2.0, "快照涨跌幅计算错误")

    fails = [m for ok, m in checks if not ok]
    return len(checks) - len(fails), fails


# ============================= 全量A股代码表 =============================
# 思路：内置 STOCK_MAP 只覆盖少量标的，个股漏检严重，故改为运行时维护一张
# 全量A股(沪/深/京)名称->代码表：本地缓存 -> 联网刷新 -> 打包内置快照 -> 脚本内置表。
EM_LIST_URL = ("https://datacenter-web.eastmoney.com/api/data/v1/get?"
               "reportName=RPT_F10_BASIC_ORGINFO"
               "&columns=SECURITY_CODE,SECURITY_NAME_ABBR,SECURITY_TYPE,TRADE_MARKET"
               "&pageNumber={page}&pageSize=5000&sortColumns=SECURITY_CODE&sortTypes=1")
A_SHARE_MARKETS = ("上海证券交易所", "深圳证券交易所", "北京证券交易所")
SINA_LIST_URL = ("http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                 "Market_Center.getHQNodeData?page={page}&num=100&sort=symbol&asc=1&node=hs_a")
STOCK_TABLE_MIN_SIZE = 1000   # 抓取结果小于该数量视为不完整，放弃更新

_STOCK_TABLE = None
_STOCK_TABLE_SOURCE = ""


def guess_market(code):
    """按代码判断市场：HS沪深主板 / CY创业板 / KCB科创板 / BJ北交所 / HK港股。"""
    code = (code or "").strip().upper()
    if not code.isdigit():
        return None
    if len(code) == 5:
        return "HK"
    if code.startswith(("688", "689")):
        return "KCB"
    if code.startswith(("300", "301")):
        return "CY"
    if code.startswith(("600", "601", "603", "605", "000", "001", "002", "003")):
        return "HS"
    if code.startswith("920") or code[0] in ("4", "8"):
        return "BJ"
    return None


def _builtin_table():
    return {name: (code, market) for name, (code, market) in STOCK_MAP.items()}


def _read_table_file(path):
    """读取 {"名称": "代码"} 或 {"名称": [代码, 市场]}，返回 {名称: (代码, 市场)}。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        return {}
    out = {}
    for name, val in raw.items():
        code = market = None
        if isinstance(val, str):
            code = val
        elif isinstance(val, (list, tuple)) and val:
            code = str(val[0])
            if len(val) > 1:
                market = val[1]
        name = str(name or "").strip()
        code = str(code or "").strip()
        market = market or guess_market(code)
        if name and code and market:
            out[name] = (code, market)
    return out


def fetch_a_shares_em(pages=10):
    """东方财富数据中心：全量A股(含风险警示板)名称与代码，约 3 秒。"""
    table = {}
    for page in range(1, pages + 1):
        data = json.loads(http_get(EM_LIST_URL.format(page=page), timeout=30,
                                   referer="https://data.eastmoney.com/"))
        result = data.get("result") or {}
        rows = result.get("data") or []
        if not rows:
            break
        for it in rows:
            code = str(it.get("SECURITY_CODE") or "").strip()
            name = str(it.get("SECURITY_NAME_ABBR") or "").strip()
            if not code or not name:
                continue
            if "A股" not in str(it.get("SECURITY_TYPE")) \
                    or str(it.get("TRADE_MARKET")) not in A_SHARE_MARKETS:
                continue
            table.setdefault(name, code)
        if page >= (result.get("pages") or 1):
            break
    return table


def fetch_a_shares_sina(pages=60):
    """新浪行情列表：全量A股名称与代码（单页上限100条，需分页）。"""
    table = {}
    for page in range(1, pages + 1):
        rows = None
        for _ in range(2):          # 单页失败重试一次，避免中途丢半张表
            try:
                rows = json.loads(http_get(SINA_LIST_URL.format(page=page), timeout=20,
                                           referer="http://finance.sina.com.cn/"))
                break
            except Exception:
                rows = None
        if not rows:
            break
        for it in rows:
            code = str(it.get("code") or "").strip()
            name = str(it.get("name") or "").strip()
            if code and name:
                table.setdefault(name, code)
    return table


def fetch_all_a_shares():
    """抓取全量A股代码表：东财数据中心优先，新浪列表兜底。"""
    for fn in (fetch_a_shares_em, fetch_a_shares_sina):
        try:
            table = fn()
        except Exception:
            continue
        if len(table) >= STOCK_TABLE_MIN_SIZE:
            return table
    return {}


def update_stock_table():
    """联网刷新全量A股代码表并写入缓存；抓取不完整或失败返回 False。"""
    global _STOCK_TABLE
    table = fetch_all_a_shares()
    if len(table) < STOCK_TABLE_MIN_SIZE:
        return False
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(STOCK_TABLE_CACHE, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, sort_keys=True)
    _STOCK_TABLE = None          # 缓存已更新，丢弃内存中的旧表
    return True


def _table_age_days(path):
    try:
        return (time.time() - os.path.getmtime(path)) / 86400.0
    except OSError:
        return None


def load_stock_table(verbose=False):
    """加载股票代码表：本地缓存 -> 联网刷新 -> 打包内置快照 -> 脚本内置映射表。"""
    global _STOCK_TABLE, _STOCK_TABLE_SOURCE
    if _STOCK_TABLE is not None:
        return _STOCK_TABLE

    def log(msg):
        if verbose:
            print(msg)

    table, source = {}, ""
    if os.path.exists(STOCK_TABLE_CACHE):
        try:
            table = _read_table_file(STOCK_TABLE_CACHE)
            if table:
                source = f"本地缓存 {len(table)} 只"
        except Exception:
            table = {}

    age = _table_age_days(STOCK_TABLE_CACHE)
    if age is None or age > STOCK_TABLE_MAX_AGE_DAYS:
        log(f"[代码表] {'缺失' if age is None else '已过期'}，正在联网刷新…")
        if update_stock_table():
            try:
                table = _read_table_file(STOCK_TABLE_CACHE)
                source = f"联网更新 {len(table)} 只"
            except Exception:
                pass
        else:
            log("[代码表] 联网刷新未成功，沿用现有数据。")

    if not table:
        snapshot = resource_path(STOCK_TABLE_SNAPSHOT)
        if os.path.exists(snapshot):
            try:
                table = _read_table_file(snapshot)
                source = f"内置快照 {len(table)} 只"
            except Exception:
                table = {}

    if not table:
        table = _builtin_table()
        source = f"脚本内置映射表 {len(table)} 只"

    # 合并脚本内置表：保留港股与品牌别名（内置优先）
    table.update(_builtin_table())

    _STOCK_TABLE = table
    _STOCK_TABLE_SOURCE = source
    log(f"[代码表] 已加载 {len(table)} 只（{source}）")
    return _STOCK_TABLE


def extract_stocks(text):
    """从消息文本提取 (名称, 代码, 市场) 列表，去重。"""
    table = load_stock_table()
    code2name = {}
    for nm, (cd, _mk) in table.items():
        code2name.setdefault(cd, nm)

    res, covered = [], []

    def taken(start, end):
        return any(not (end <= cs or start >= ce) for cs, ce in covered)

    def add(name, code, market, start, end):
        if taken(start, end):
            return
        covered.append((start, end))
        res.append((name, code, market))

    # 1) 文本内直接带代码：名称（代码）、名称（688825.SH）
    #    代码是权威的，名称一律以代码反查的官方简称为准，
    #    否则"近日记者走进扎根合肥高新区的国仪公司（688828）"会把前面十几个字当成股票名。
    for m in re.finditer(r"([\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z0-9]{1,14})\s*[（(]\s*(\d{5,6})"
                         r"\s*(?:\.\s*(?:SH|SZ|SS|BJ|HK))?\s*[）)]", text, re.IGNORECASE):
        code = m.group(2)
        market = guess_market(code)
        if market:
            add(code2name.get(code, m.group(1)), code, market, m.start(), m.end())

    # 2) 带市场后缀的裸代码：688825.SH / 601127.SZ
    for m in re.finditer(r"(?<![\d.])(\d{6})\s*\.\s*(SH|SZ|SS|BJ)(?![\w.])", text, re.IGNORECASE):
        code = m.group(1)
        market = guess_market(code)
        if market:
            add(code2name.get(code, code), code, market, m.start(), m.end())

    # 3) 全量名称匹配（长名优先，已被占用的区间跳过，避免"茅台"命中"贵州茅台"）
    for name in sorted(table, key=len, reverse=True):
        if len(name) < 2 or name.endswith("退") or name not in text:
            continue
        code, market = table[name]
        start = 0
        while True:
            idx = text.find(name, start)
            if idx < 0:
                break
            if taken(idx, idx + len(name)):
                start = idx + 1
                continue
            if name in AMBIGUOUS_NAMES and not _strong_context(text, idx, len(name), table):
                start = idx + 1
                continue
            if name in SOURCE_ORGS and _is_news_source(text, idx, len(name)):
                start = idx + 1
                continue
            add(name, code, market, idx, idx + len(name))
            break

    # 去重（同代码保留首条），并剔除 ST/*ST/退市股
    seen, out = set(), []
    for name, code, market in res:
        if code in seen or is_st_name(name):
            continue
        seen.add(code)
        out.append((name, code, market))
    return out


def classify(text):
    """利好分类：按关键词为消息归类，返回得分最高的类别名（硬类别在平局时优先）。"""
    order_ok = (any(w in text for w in ORDER_STRONG) or ORDER_AMOUNT_PAT.search(text))
    best, best_score = "其他", 0
    for cat, kws in CATEGORIES:
        if cat == "订单/合同" and not order_ok:
            continue        # 只有"签订/合同/签约"这类弱动词：证据不足，不计入订单类
        score = sum(1 for k in kws if k in text)
        if score > best_score:
            best, best_score = cat, score
    return best


def classify_negative(text):
    """利空分类：返回 (最严重类别, 命中类别列表)；无利空返回 (None, [])。"""
    hits = [cat for cat, kws in NEG_CATEGORIES if any(k in text for k in kws)]
    if not hits:
        return None, []
    # "终止减持""承诺不减持""当日暂无…拟减持"这类否定式表述是利好侧事件，
    # 剔除减持类命中；若还有其他利空类别，仍按剩余类别计。
    if "减持/抛售" in hits and (any(w in text for w in NEG_TERMINATED)
                                or NEG_DENIED_PAT.search(text)):
        hits = [c for c in hits if c != "减持/抛售"]
        if not hits:
            return None, []
    # "解除司法冻结/撤销冻结"是风险出清，同样不是利空；若还有其他利空类别，仍按剩余类别计。
    if "冻结/司法/担保" in hits and NEG_RELEASE_PAT.search(text):
        hits = [c for c in hits if c != "冻结/司法/担保"]
        if not hits:
            return None, []
    return max(hits, key=lambda c: NEG_LEVEL.get(c, 1)), hits


def judge_neg_level(text, neg_cat):
    """利空严重程度：基础等级按具体表述上浮/下调（1~3）。"""
    base = NEG_LEVEL.get(neg_cat, 1)
    # 刑事/重大违法类直接封顶 N3
    if any(w in text for w in ("刑事立案", "涉嫌欺诈", "涉嫌信披违法", "涉嫌内幕交易",
                               "重大违法", "情节严重", "特别重大")):
        return 3
    # 「冻结/司法/担保」原一刀切判 N3，但 30 日回测里该类 17 条全是股东股份被司法冻结，
    # 平均超额 -0.00%、下跌命中率 47.1%，比 N2（53.5%）还差 —— 已整类降为 N2（见 NEG_LEVEL）。
    # 减持比例不足 1% 降为 N1（只认紧邻"减持"的百分比，避免取到文中无关数字）
    if neg_cat == "减持/抛售":
        m = re.search(r"减持[^。；]{0,30}?([0-9]+(?:\.[0-9]+)?)\s*%", text) \
            or re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%[^。；]{0,20}?减持", text)
        if m and float(m.group(1)) < 1.0:
            return 1
    # 纯问询函（非警示函/监管函）降为 N1
    if neg_cat == "处罚/监管措施" and "问询函" in text \
            and "警示函" not in text and "监管函" not in text and "监管措施" not in text:
        return 1
    return base


# ======================== 套壳/程式化公告识别 & 他人事件误挂 ========================
# 依据：参考目录的 L5 观察池（2026-09-21~28）里，96 只被判 L5「硬利好」的标的中
# 81 只下跌、平均 -2.57%。逐条比对后发现两类系统性假信号：
#   1) 没有实质利好含量的程式化公告 —— 募集资金监管协议、回购事项前十大股东持股情况、
#      限制性股票回购注销、通知债权人、中介机构意见书、回购进展/结果、增持已实施完成…
#      （关键词"签订/回购/增持"照样命中，但市场完全无感）；
#   2) 他人事件被误挂到本股 —— 例如"广发证券"名下挂着它给永安林业出具的核查意见。
# 下面的规则把它们从利好侧剔除或降级，使"关键词命中"不再等于"硬利好"。
BOILER_DROP = "剔除"        # 无信息量，不计入任何明细
BOILER_DOWN1 = "降一级"
BOILER_DOWN2 = "降两级"
BOILER_TO_NEG = "转利空"    # 名义上是"回购"相关，实际是增加流通盘的减持行为

# (正则, 处置, 说明)；顺序敏感，先匹配到的先生效
BOILERPLATE_RULES = [
    # 「出售已回购股份」名义挂在"回购"下，实为向二级市场抛售，排在所有回购规则之前
    (re.compile(r"出售[^。；]{0,8}已回购股份|已回购股份[^。；]{0,8}出售"), BOILER_TO_NEG, "出售已回购股份"),
    (re.compile(r"致歉|纰漏|修订痕迹|上传(?:失误|错误|纰漏)|复核未(?:覆盖|发现)|"r"信披(?:瑕疵|失误|违规)|公告(?:更正|勘误)"), BOILER_DROP, "信披瑕疵/更正致歉"),
    # 担保/质押/贷款类常因"合同""签署""融资"等词被误判为利好，实质是增加风险敞口。
    # 30 日回测：命中该类文案的 13 条利好平均超额 -0.81%、胜率仅 30.8%，故整类剔除。
    (re.compile(r"提供[^。；]{0,10}担保|担保额度|保证合同|履约担保|抵押担保|质押合同|股权质押"
                r"|再质押|解质押|并购贷款|委托贷款"), BOILER_DROP, "担保/质押/贷款类"),
    (MACRO_POLICY_PAT, BOILER_DROP, "宏观政策问答/解读"),
    (BOARD_MOVE_PAT, BOILER_DROP, "盘面异动/热点汇总"),
    (re.compile(r"募集资金专户|募集资金[^。；]{0,8}监管协议|[三四五]方监管协议"), BOILER_DROP, "募集资金监管协议"),
    (re.compile(r"回购[^。；]{0,6}(?:前十|前10)|前(?:十|10)名股东[^。；]{0,10}持股情况"), BOILER_DROP, "回购前十大股东持股情况"),
    (re.compile(r"限制性股票[^。；]{0,8}回购注销|回购注销[^。；]{0,10}(?:限制性股票|首次授予)"), BOILER_DROP, "限制性股票回购注销"),
    (re.compile(r"回购(?:股份)?注销|注销[^。；]{0,8}已?回购股份"), BOILER_DROP, "回购股份注销"),
    (re.compile(r"通知债权人|减少注册资本"), BOILER_DROP, "通知债权人/减资"),
    (re.compile(r"法律意见书|法律意见|核查意见|保荐[^。；]{0,8}意见|律师[^。；]{0,6}意见"), BOILER_DROP, "中介机构意见书"),
    (re.compile(r"(?:权益分派|利润分配)[^。；]{0,24}调整回购股份?价格上限"), BOILER_DROP, "调整回购价格上限"),
    (re.compile(r"回购期限过半|尚未实施回购|未实施回购"), BOILER_DROP, "回购尚未实施"),
    (re.compile(r"质押式回购"), BOILER_DROP, "股东质押（非公司回购）"),
    (re.compile(r"简式权益变动报告书|详式权益变动报告书"), BOILER_DOWN1, "权益变动报告书"),
    (re.compile(r"回购[^。；]{0,8}(?:实施结果|结果|进展|达到)"), BOILER_DOWN1, "回购进展/结果类"),
    (re.compile(r"(?:员工|核心员工)?持股计划[^。；]{0,12}非交易过户"), BOILER_DOWN1, "员工持股计划过户"),
    (re.compile(r"(?:增持计划|增持)[^。；]{0,8}(?:实施完成|实施完毕|已完成|进展|触及)"), BOILER_DOWN1, "增持进展/已完成"),
]

# 快讯源里个股名与事件同处一句时，名号须落在句首附近；靠后提及的多半是别人家的事。
GUEST_HEAD_LIMIT = 20


def boilerplate_action(text):
    """返回 (处置, 说明)；未命中返回 (None, "")。"""
    for pat, act, desc in BOILERPLATE_RULES:
        if pat.search(text):
            return act, desc
    return None, ""


def is_guest_stock(source, text, name, code):
    """该个股是否只是"被顺带提及"（他人事件误挂）。
    公告源：摘要由本程序拼成"简称(代码)：标题"，若不以本股开头，说明是中介机构为他人出具的文件；
    快讯源：个股名/代码须落在所属分句的前 GUEST_HEAD_LIMIT 字符内。"""
    if not name:
        return False
    if source == CNINFO_SOURCE_NAME:
        # 公告摘要由本程序拼成"简称(代码)：标题"，取开头那段主体，代码对得上就不是误挂
        m = re.match(r"^([^()（）]{1,16})[（(](\d{6})[）)]", text)
        return not (m and m.group(2) == code)
    for clause in _CLAUSE_SPLIT.split(text):
        idx = clause.find(name)
        if idx < 0 and code:
            idx = clause.find(str(code))
        if idx >= 0:
            return idx > GUEST_HEAD_LIMIT
    return False


# 分句：句末标点/换行/圈号，以及"7、"这类编号列表项。
# 目的：一条"新闻精选"类汇总快讯里，"公司新闻方面：①A公司…④B公司被立案"整体只有一个句号，
# 若不分句，立案/处罚等负面词会误挂到同一条快讯提到的所有个股上。
_CLAUSE_SPLIT = re.compile(r"[。；！？\r\n]|[①②③④⑤⑥⑦⑧⑨⑩]|(?:(?<=[\s：:])|^)\d{1,2}、")


def negative_words(text, cats):
    """返回命中的利空关键词（用于报告展示与主体校验）。"""
    words = []
    for cat, kws in NEG_CATEGORIES:
        if cat in cats:
            words += [k for k in kws if k in text]
    return words


def negative_clause(text, name, code, words):
    """返回"负面关键词与个股同处一句"的那个分句；无则返回 None（不算该股利空）。
    典型误判：汇总快讯"7、公司新闻方面：①行云科技：签订合同。④川大智胜：被立案"
    会把立案挂到行云科技、阿里巴巴等无关个股上，而摘要也会显示成无关的栏目开头。"""
    if not words:
        return None
    for clause in _CLAUSE_SPLIT.split(text):
        if not clause:
            continue
        if not any(w in clause for w in words):
            continue
        if name in clause or (code and code in clause):
            return clause.strip()
    return None


def is_positive(text, cat):
    """判断是否个股利好：命中利好类别，且不含风险警示/负面词、未命中利空类别（利好利空互斥）。"""
    if has_st_tag(text) or any(k in text for k in EXCLUDE_FOR_POSITIVE):
        return False
    if any(k in text for k in EXCLUDE_KEYWORDS):
        return False
    if classify_negative(text)[0]:
        return False
    return cat != "其他"


def is_negative(text):
    """判断是否个股利空：命中利空类别，且不含泛情绪词。"""
    if any(k in text for k in EXCLUDE_FOR_NEGATIVE):
        return False
    return classify_negative(text)[0] is not None


def has_landing(text):
    """是否包含"事件已确认落地"信号。"""
    if any(w in text for w in LANDING_WORDS):
        return True
    return any(re.search(p, text) for p in LANDING_PATTERNS)


def judge_level_tier(text, cat):
    """利好五级评级 + 两层级判定，返回 (level 1~5, tier)。
    落地词优先于计划态词：同一句里既"已签署"又"拟扩产"时按已落地处理，避免把落地事件打成 L1。"""
    if cat not in BASE_LEVEL:
        return None, None
    level, tier = BASE_LEVEL[cat]
    landed = has_landing(text)
    rumor = any(w in text for w in RUMOR_WORDS) and not landed

    if cat == "订单/合同":
        return (2, TIER_CONCEPT) if rumor else (5, TIER_LANDED)

    if cat == "增持/回购/分红":
        return (3, TIER_CONCEPT) if rumor else (5, TIER_LANDED)

    if cat == "技术/产品突破":
        if rumor:
            return 2, TIER_CONCEPT
        if any(w in text for w in SOFT_TECH_WORDS) and not any(
                w in text for w in ("量产", "交付", "获批", "批件", "投产", "出货", "验证通过")):
            return 2, TIER_CONCEPT      # 仅发布/上线/亮相，非量产交付
        return 4, TIER_LANDED

    if cat == "扩产/投资":
        if rumor:
            return 2, TIER_CONCEPT
        # 明确“未落地/仍在推进”的否定式表述：不能按 L3 强催化处理
        if any(w in text for w in ("尚未完成", "尚未实施", "尚未签署", "尚未落地",
                                   "仍在推进", "推进中", "尚未过户", "尚未交割")):
            return 2, TIER_CONCEPT
        if any(w in text for w in ("投产", "达产", "竣工", "建成投产", "完成收购", "过户",
                                   "完成交割", "交割完成", "已交割")):
            return 3, TIER_LANDED       # 资本开支/股权交易已兑现
        return 3, TIER_CONCEPT

    # 合作/经营改善/传闻类
    if rumor:
        level = min(level, 2)
    return level, TIER_CONCEPT


# ==================== 关键词证据层（v2.0，依据 30 日回测校准） ====================
# 数据来源：--review 30（2026-08-31 ~ 2026-09-29，1457 条利好有 T+1 行情）的「关键词胜率榜」。
# 入表门槛：样本 ≥ 20，且 23 日 / 30 日两次回测方向一致 —— 早期 23 日样本里「增资」曾以
# 5 条 100% 居首、被当作强信号；扩到 30 日后只剩 34 条 52.9%，小样本结论不可外推。
#   弱证据（胜率 ≤45% 且平均超额为负）：拟 40.2%/107、量产 39.3%/28、投产 39.1%/23、
#                                      出货 35.0%/20、订单 44.2%/43、合作协议 39.3%/28
#   强证据（胜率 ≥55% 且平均超额为正）：回购 55.4%/359、增持 58.4%/137、
#                                      收购 60.6%/33、回升 57.7%/26
EV_WEAK = ("拟", "量产", "投产", "出货", "订单", "合作协议")
EV_STRONG = ("回购", "增持", "收购", "回升")


def evidence_adjust(text, level, tier):
    """按回测证据微调评级：命中弱证据词、且未同时命中强证据词时降一级（不低于 L1）。
    返回 (level, tier, 是否调档)。"""
    if not any(w in text for w in EV_WEAK) or any(w in text for w in EV_STRONG):
        return level, tier, False
    lv = max(1, level - 1)
    if lv == level:
        return level, tier, False
    return lv, (tier if lv >= 3 else TIER_CONCEPT), True


def resolve_positive(text, cat):
    """利好侧的最终处置，run_extract 与 run_review 共用，保证"报告口径"与"回测口径"一致。
    返回 (action, level, tier, note)：
      action = BOILER_DROP    整条剔除，不计入明细；
      action = BOILER_TO_NEG  名为回购实为抛售，转记利空；
      action = None           计入利好，level/tier 有效；note 为降级原因（回测按此归类）。"""
    act, desc = boilerplate_action(text)
    if act in (BOILER_DROP, BOILER_TO_NEG):
        return act, None, None, desc
    level, tier = judge_level_tier(text, cat)
    if level is None:
        return None, None, None, ""
    level, tier, ev = evidence_adjust(text, level, tier)
    if act in (BOILER_DOWN1, BOILER_DOWN2):
        level = max(1, level - (1 if act == BOILER_DOWN1 else 2))
        if level <= 2:
            tier = TIER_CONCEPT
        return None, level, tier, desc
    # 机构观点/研报条（【中信建投：医疗器械板块拐点来临】、【中信证券：维持三一重工"买入"评级】）：
    # 个股只是被点到的观点标的，事件并未落地 —— 降一级、层级固定『概念发酵』。
    # 30 日实测 11 条（8 条有行情：平均 +0.68%、胜率 75%），小样本且方向为预期型，按预期型定档更稳。
    if is_org_view_item(text):
        return None, max(1, level - 1), TIER_CONCEPT, "机构观点条降级"
    return None, level, tier, ("回测证据降级" if ev else "")


def build_stats(records, is_negative=False):
    """汇总评级/层级统计，供报告使用。"""
    if is_negative:
        stats = {"total": len(records), "level": {l: 0 for l in (1, 2, 3)}}
        for r in records:
            stats["level"][r["neg_level"]] = stats["level"].get(r["neg_level"], 0) + 1
        return stats
    stats = {"total": len(records), "level": {l: 0 for l in (1, 2, 3, 4, 5)},
             "tier": {TIER_LANDED: 0, TIER_CONCEPT: 0}}
    for r in records:
        stats["level"][r["level"]] = stats["level"].get(r["level"], 0) + 1
        stats["tier"][r["tier"]] = stats["tier"].get(r["tier"], 0) + 1
    return stats


def dedup_sort(records, key_fn, sort_key):
    """按 key_fn 去重后按 sort_key 排序（利好：先落地层级、再评级高低；利空：先严重程度）。"""
    seen, uniq = set(), []
    for r in records:
        k = key_fn(r)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    uniq.sort(key=sort_key)
    return uniq


def pick_theme(text):
    for name, kws in THEMES:
        if any(k in text for k in kws):
            return name
    return None


def backfill_cache_path(report_date):
    """回补缓存文件路径：个股利好报告/_回补缓存/YYYYMMDD.json"""
    d = report_date.date() if hasattr(report_date, "date") else report_date
    return os.path.join(BACKFILL_DIR, d.strftime("%Y%m%d") + ".json")


def dump_backfill_cache(report_date, mode, day_news, pos_records, neg_records,
                        ok_sources, fail_sources, window_desc, filt=None):
    """把当日结构化结果落盘，供行情验证与规则回测直接读取，避免回头解析 Markdown。"""
    os.makedirs(BACKFILL_DIR, exist_ok=True)
    d = report_date.date() if hasattr(report_date, "date") else report_date
    payload = {
        "report_date": d.strftime("%Y-%m-%d"),
        "mode": mode,
        "window": window_desc,
        "news_count": len(day_news),
        "sources_ok": ok_sources,
        "sources_fail": fail_sources,
        "filter": filt or {},
        "records": pos_records,
        "neg_records": neg_records,
    }
    path = backfill_cache_path(report_date)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return path


def run_backfill(days=30, log=print):
    """批量回补最近 days 天：逐日生成报告 + 落盘结构化缓存（已有缓存的日期直接跳过）。
    超过 MAX_HISTORY_DAYS 的日期只取巨潮公告 —— 快讯源逐页回溯成本随天数线性上涨。"""
    if days < 1 or days > MAX_HISTORY_DAYS_CNINFO:
        log(f"回补天数需在 1~{MAX_HISTORY_DAYS_CNINFO} 之间，当前为 {days}")
        return
    today = datetime.date.today()
    os.makedirs(BACKFILL_DIR, exist_ok=True)
    done, skipped, failed = 0, 0, 0
    log(f"[回补] 目标：最近 {days} 天，逐日抓取并落盘（已有缓存的日期自动跳过）")
    for i in range(days, 0, -1):
        day = today - datetime.timedelta(days=i)
        d = datetime.datetime.combine(day, datetime.time(0, 0))
        if os.path.exists(backfill_cache_path(d)):
            log(f"[跳过] {day:%Y-%m-%d} 已有缓存")
            skipped += 1
            continue
        try:
            log(f"[回补] {day:%Y-%m-%d} 抓取中…")
            run_extract(d, mode="回补", dump_cache=True)
            done += 1
        except Exception as e:
            log(f"[失败] {day:%Y-%m-%d} {type(e).__name__}: {e}")
            failed += 1
    log(f"[回补完成] 新增 {done} 天 / 跳过 {skipped} 天 / 失败 {failed} 天；缓存目录：{BACKFILL_DIR}")


# ============================= 规则回测（读缓存 + 行情，不联网取材） =============================
# 目的：把"利好/利空判定条件"放到真实涨跌上检验 —— 用全部样本的 T+1 相对基准超额收益，
# 回看每一档评级、每一个类别、每一个关键词到底站不站得住，再据此微调评级。
REVIEW_MIN_SAMPLE = 5      # 关键词胜率榜的最小样本数（样本太小的不进榜，避免噪声当规律）

_CAT_KEYS = dict(CATEGORIES)


def load_backfill_caches(days=MAX_HISTORY_DAYS_CNINFO, log=print):
    """读取最近 days 天的回补缓存（按日期升序），返回 [payload, ...]。"""
    if not os.path.isdir(BACKFILL_DIR):
        return []
    today = datetime.date.today()
    out = []
    for fn in sorted(os.listdir(BACKFILL_DIR)):
        if not fn.endswith(".json"):
            continue
        try:
            d = datetime.datetime.strptime(fn[:-5], "%Y%m%d").date()
        except ValueError:
            continue
        if (today - d).days > days:
            continue
        try:
            with open(os.path.join(BACKFILL_DIR, fn), encoding="utf-8") as f:
                out.append(json.load(f))
        except Exception as e:
            log(f"[回测] 跳过 {fn}：{type(e).__name__}: {e}")
    return out


def stat_of(vals):
    """(样本数, 平均超额%, 胜率%)；无样本返回 (0, None, None)。"""
    if not vals:
        return 0, None, None
    n = len(vals)
    return n, round(sum(vals) / n, 2), round(sum(1 for v in vals if v > 0) / n * 100, 1)


def review_table(lines, title, buckets, head=("分组", "样本", "平均超额", "胜率"),
                 min_sample=1, sort_by_sample=True):
    """往 lines 追加一张分组统计表；buckets 为 {组名: [超额...]}。"""
    rows = [(k, ) + stat_of(v) for k, v in buckets.items() if len(v) >= min_sample]
    if not rows:
        return False
    rows.sort(key=(lambda r: (-r[1], r[0])) if sort_by_sample else (lambda r: r[0]))
    lines += [f"**{title}**", "",
              f"| {head[0]} | {head[1]} | {head[2]} | {head[3]} |", "|---|---:|---:|---:|"]
    for k, n, avg, win in rows:
        lines.append(f"| {k} | {n} | {fmt_pct(avg)} | {'' if win is None else f'{win}%'} |")
    lines.append("")
    return True


def run_review(days=MAX_HISTORY_DAYS_CNINFO, log=print):
    """生成《规则回测》报告：把近 N 天回补缓存里的每条利好/利空，按真实 T+1 涨跌回头检验。
    只读本地缓存 + 已标注行情，不重新联网抓新闻。"""
    caches = load_backfill_caches(days, log=log)
    if not caches:
        log(f"[回测] {BACKFILL_DIR} 下没有可用缓存，请先执行：--backfill {days}")
        return None

    pos, neg = [], []
    filt_sum = {"套壳公告": 0, "他人事件误挂": 0, "降级": 0}
    for c in caches:
        day = c.get("report_date") or ""
        for r in c.get("records") or []:
            pos.append(dict(r, day=day))
        for r in c.get("neg_records") or []:
            neg.append(dict(r, day=day))
        for k, v in (c.get("filter") or {}).items():
            filt_sum[k] = filt_sum.get(k, 0) + v

    # 按「当前规则」重算：缓存里的 level/tier/neg_level 是当初落盘时的旧规则结果。
    # 调完规则若沿用旧值，回测就成了历史快照而不是回归测试 —— 所以这里用 run_extract 同款的
    # resolve_positive / classify_negative / judge_neg_level 重新过一遍，使「调档前 vs 调档后」
    # 可以在不重新联网取材的前提下直接对比。
    pos_scored, changed, dropped, to_neg = [], 0, 0, 0
    for r in pos:
        full = r.get("full") or r.get("text") or ""
        cat = classify(full)
        action, lv, tr, note = resolve_positive(full, cat)
        if action == BOILER_TO_NEG:
            to_neg += 1
            continue
        if action == BOILER_DROP or lv is None:
            dropped += 1
            continue
        if (lv, tr) != (r.get("level"), r.get("tier")):
            changed += 1
        pos_scored.append(dict(r, cat=cat, level=lv, tier=tr, boilerplate=note))
    pos = pos_scored
    neg_scored, n_changed, n_dropped = [], 0, 0
    for r in neg:
        # 与 run_extract 同款口径：利空档位按「该个股所在分句」判（缓存里的 text 就是当时的分句），
        # 用全文重算会重演汇总快讯的跨句串味，使"报告口径 ≠ 回测口径"。
        clause = r.get("text") or r.get("full") or ""
        nc, _ = classify_negative(clause)
        nl = judge_neg_level(clause, nc) if nc else None
        if nc is None:
            if boilerplate_action(r.get("full") or clause)[0] == BOILER_TO_NEG:
                nc, nl = "减持/抛售", 1          # 「出售已回购股份」转来的利空，按现规则仍是利空
            elif NEG_RELEASE_PAT.search(clause):
                n_dropped += 1                   # 「解除冻结」类：现规则下整条不算利空
                continue
            else:
                nc, nl = r.get("neg_cat"), r.get("neg_level")   # 分句被截断等失上下文，沿用旧值
        elif nl != r.get("neg_level"):
            n_changed += 1
        neg_scored.append(dict(r, neg_cat=nc, neg_level=nl))
    neg = neg_scored
    filt_sum["降级"] = sum(1 for r in pos if r.get("boilerplate"))

    first, last = caches[0].get("report_date", ""), caches[-1].get("report_date", "")
    pos_v = [r for r in pos if r.get("exc_t1") is not None]
    neg_v = [r for r in neg if r.get("exc_t1") is not None]

    lines = [f"# 规则回测报告（近 {days} 天）", "",
             f"- **样本区间**：{first} ~ {last}（覆盖 {len(caches)} 个交易日）",
             f"- **生成时间**：{datetime.datetime.now():%Y-%m-%d %H:%M}",
             f"- **验证口径**：T+1 相对基准指数（沪→上证指数 / 深北→深证综指）的超额收益；"
             f"利好侧超额为正即算命中，利空侧超额为负即算命中",
             f"- **规则口径**：按当前代码中的判定规则对缓存重新打分 —— 本次重算"
             f"利好改档/剔除 {changed + dropped + to_neg} 条、利空改档 {n_changed} 条"
             f"、利空剔除 {n_dropped} 条"
             f"（调档前后可直接对比本报告）",
             f"- **样本**：利好 {len(pos)} 条（有 T+1 行情 {len(pos_v)} 条）、"
             f"利空 {len(neg)} 条（有 T+1 行情 {len(neg_v)} 条）",
             f"- **过滤汇总**：提取时剔除套壳/程式化公告 {filt_sum.get('套壳公告', 0)} 条、"
             f"他人事件误挂 {filt_sum.get('他人事件误挂', 0)} 条；"
             f"按当前规则重算后共降级 {filt_sum.get('降级', 0)} 条",
             ""]

    # 一、利好评级
    lines += ["## 一、利好评级 vs 实际表现", ""]
    all_p = [r["exc_t1"] for r in pos_v]
    n, avg, win = stat_of(all_p)
    lines += [f"全样本：{n} 条，平均超额 **{fmt_pct(avg)}**，胜率 **{win}%**", ""]
    review_table(lines, "按评级（L5→L1）",
                 {LEVEL_NAME[lv]: [r["exc_t1"] for r in pos_v if r["level"] == lv]
                  for lv in (5, 4, 3, 2, 1)})
    review_table(lines, "按层级", {t: [r["exc_t1"] for r in pos_v if r["tier"] == t]
                                 for t in (TIER_LANDED, TIER_CONCEPT)})

    # 二、利好类别
    lines += ["## 二、利好类别 vs 实际表现", ""]
    review_table(lines, "按事件类别", {c: [r["exc_t1"] for r in pos_v if r["cat"] == c]
                                     for c, _ in CATEGORIES},
                 min_sample=REVIEW_MIN_SAMPLE)

    # 三、关键词胜率榜（只统计该条被判定的类别下的关键词，避免跨类污染）
    kw = {}
    for r in pos_v:
        for k in _CAT_KEYS.get(r["cat"], []):
            if k in (r.get("full") or ""):
                kw.setdefault(k, []).append(r["exc_t1"])
    ranked = [(k,) + stat_of(v) for k, v in kw.items() if len(v) >= REVIEW_MIN_SAMPLE]
    ranked.sort(key=lambda x: (-x[3], -x[1]))
    lines += ["## 三、利好关键词胜率榜", "",
              f"仅统计命中数 ≥ {REVIEW_MIN_SAMPLE} 的关键词。", ""]
    if ranked:
        lines += ["| 关键词 | 所属类别 | 样本 | 平均超额 | 胜率 |", "|---|---|---:|---:|---:|"]
        for k, n, a, w in ranked:
            cat = next((c for c, ks in CATEGORIES if k in ks), "—")
            lines.append(f"| {k} | {cat} | {n} | {fmt_pct(a)} | {w}% |")
        lines.append("")
    else:
        lines += ["样本量不足，暂无可用榜单。", ""]

    # 四、被降级的条目（套壳/程式化 + 回测证据）
    lines += ["## 四、降级条目（套壳/程式化 + 回测证据）的实际表现", ""]
    bp = {}
    for r in pos_v:
        if r.get("boilerplate"):
            bp.setdefault(r["boilerplate"], []).append(r["exc_t1"])
    if review_table(lines, "按降级原因", bp):
        lines += ["本条为「降级后」样本；被完全剔除的条目已不在明细中，"
                  "其数量见上方「过滤汇总」。", ""]
    else:
        lines += ["区间内无被降级条目。", ""]

    # 五、利空侧（方向相反：超额越负越准）
    lines += ["## 五、利空等级 vs 实际表现", "",
              "利空侧看的是「跌没跌」：超额收益越负，说明该利空越被市场认可。", ""]
    if neg_v:
        all_n = [r["exc_t1"] for r in neg_v]
        n2, avg2, win2 = stat_of(all_n)
        hit = round(sum(1 for v in all_n if v < 0) / len(all_n) * 100, 1)
        lines += [f"全样本：{n2} 条，平均超额 **{fmt_pct(avg2)}**，下跌命中率 **{hit}%**"
                  f"（超额<0 视为命中）", ""]
        for lv in (3, 2, 1):
            vals = [r["exc_t1"] for r in neg_v if r["neg_level"] == lv]
            if not vals:
                continue
            na, av, _ = stat_of(vals)
            hl = round(sum(1 for v in vals if v < 0) / na * 100, 1)
            lines.append(f"- {NEG_LEVEL_NAME[lv]}：{na} 条，平均超额 {fmt_pct(av)}，"
                         f"下跌命中率 {hl}%")
        lines.append("")
        ncb = {}
        for r in neg_v:
            ncb.setdefault(r["neg_cat"], []).append(r["exc_t1"])
        rows = sorted(((k, len(v), round(sum(v) / len(v), 2),
                        round(sum(1 for x in v if x < 0) / len(v) * 100, 1))
                       for k, v in ncb.items()), key=lambda x: (-x[1], x[0]))
        if rows:
            lines += ["| 利空类别 | 样本 | 平均超额 | 下跌命中率 |", "|---|---:|---:|---:|"]
            for k, na, av, hl in rows:
                lines.append(f"| {k} | {na} | {fmt_pct(av)} | {hl}% |")
            lines.append("")
    else:
        lines += ["区间内利空样本不足。", ""]

    # 六、结论与调档建议（全部由上述数据推导，不做主观判断）
    lines += ["## 六、结论与调档建议", ""]
    tips = []
    if ranked:
        good = [k for k, n, a, w in ranked if w >= 60]
        bad = [k for k, n, a, w in ranked if w <= 40]
        if good:
            tips.append(f"胜率 ≥60% 的关键词（{ '、'.join(good[:12]) }）可作为 L5/L4 的强信号保留。")
        if bad:
            tips.append(f"胜率 ≤40% 的关键词（{ '、'.join(bad[:12]) }）中，样本 ≥20 的已按证据降一级，"
                        f"其余样本不足不下调（小样本 100% 胜率不可外推）。")
        tips.append(f"已生效的证据调档：弱证据词（{ '、'.join(EV_WEAK) }）降一级、"
                    f"并对其余命中强证据词（{ '、'.join(EV_STRONG) }）的条目豁免降级；"
                    f"入表门槛为样本 ≥20 且两次回测方向一致。")
    lv5 = [r["exc_t1"] for r in pos_v if r["level"] == 5]
    if lv5:
        n5, a5, w5 = stat_of(lv5)
        tips.append(f"L5 硬利好 {n5} 条，平均超额 {fmt_pct(a5)}，胜率 {w5}%"
                    + ("；与 L2/L3 差异不显著，说明「关键词命中」仍偏宽，需继续收紧套壳类公告。"
                       if w5 is not None and w5 < 50 else "；具备一定区分度。"))
    if filt_sum.get("套壳公告"):
        tips.append(f"区间内共剔除套壳/程式化公告 {filt_sum['套壳公告']} 条 —— "
                    f"占原始命中量的比重越高，说明历史版本的「硬利好」噪声越大。")
    if neg_v:
        n3 = [r["exc_t1"] for r in neg_v if r["neg_level"] == 3]
        n1 = [r["exc_t1"] for r in neg_v if r["neg_level"] == 1]
        if n3 and n1:
            _, a3, _ = stat_of(n3)
            _, a1, _ = stat_of(n1)
            if a3 is not None and a1 is not None and a3 < a1:
                tips.append(f"N3 平均超额 {fmt_pct(a3)} 比 N1 的 {fmt_pct(a1)} 更负，利空分级方向正确；"
                            f"利空侧已按证据把「冻结/司法/担保」整类由 N3 降为 N2"
                            f"（该类实测下跌命中率低于 N2 整体）。")
    if not tips:
        tips.append("样本不足，暂不给出调档建议，请先扩大回补天数。")
    lines += [f"- {t}" for t in tips] + [""]

    out = os.path.join(REPORT_DIR, f"规则回测_{first.replace('-', '')}_{last.replace('-', '')}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"[回测] 样本区间 {first} ~ {last}；利好 {len(pos_v)}/{len(pos)} 条、"
        f"利空 {len(neg_v)}/{len(neg)} 条有 T+1 行情")
    log(f"[回测] 报告已生成：{out}")
    return out


def run_extract(report_date, mode="手动", rolling=False, window_hours=24, dump_cache=False):
    """执行一次抓取+提取+报告生成。返回报告文件路径。
    rolling=True 抓取"最近 window_hours 小时"滚动窗口；
    否则抓取 report_date 当天 00:00~24:00 —— 历史日期会翻页/游标回溯，最多回溯 MAX_HISTORY_DAYS 天。
    """
    os.makedirs(REPORT_DIR, exist_ok=True)
    now = datetime.datetime.now()
    target = report_date.date() if hasattr(report_date, "date") else report_date
    is_history = (not rolling) and target != now.date()

    # 0) 股票代码表（首次或过期时联网刷新）
    load_stock_table(verbose=True)

    # 1) 时间窗口 [start, end)
    if rolling:
        end = now
        start = end - datetime.timedelta(hours=window_hours)
    else:
        start = datetime.datetime.combine(target, datetime.time(0, 0))
        end = start + datetime.timedelta(days=1)
    back_days = (now.date() - target).days if is_history else 0
    if is_history and back_days > MAX_HISTORY_DAYS_CNINFO:
        raise RuntimeError(
            f"{target:%Y-%m-%d} 距今 {back_days} 天，超出可回溯上限 "
            f"{MAX_HISTORY_DAYS_CNINFO} 天（超过 {MAX_HISTORY_DAYS} 天的日期仅取巨潮公告）。")
    date_str = report_date.strftime("%Y-%m-%d")

    # 2) 抓取：窗口内回溯（历史日期逐页翻到目标时段，耗时随回溯天数增加）
    news, ok_sources, fail_sources = fetch_news(start, end, history=is_history,
                                               days_back=back_days)
    day_news = [n for n in news if in_window(n.get("time") or "", start, end)]
    day_news.sort(key=lambda x: x.get("time", ""))
    if rolling:
        window_desc = f"最近 {window_hours} 小时（{start:%m-%d %H:%M} ~ {end:%m-%d %H:%M}）"
    elif is_history:
        window_desc = f"{date_str} 全天（{start:%m-%d %H:%M} ~ {end:%m-%d %H:%M}）"
    else:
        window_desc = f"{date_str} 全天（截至 {now:%m-%d %H:%M}）"
    if not day_news:
        # 如实告知抓不到，绝不用"最新一页"冒充该日数据
        window_desc += "｜窗口内未抓取到任何消息"

    # 3) 提取个股利好 + 个股利空（利好利空互斥：有明显利空的个股不进利好）
    pos_records, neg_records = [], []
    filt = {"套壳公告": 0, "他人事件误挂": 0, "降级": 0}
    for n in day_news:
        text = n["text"]
        source = n.get("source", "")
        stocks = extract_stocks(text)
        if not stocks:
            continue
        cat = classify(text)
        pos_ok = is_positive(text, cat)
        neg_cat, neg_hits = classify_negative(text)
        # 利好侧最终处置（套壳剔除/转利空 + 基础评级 + 回测证据调档），与 run_review 同一函数
        if pos_ok:
            action, level, tier, b_note = resolve_positive(text, cat)
        else:
            action, level, tier, b_note = None, None, None, ""
        if not pos_ok and not neg_cat:
            continue
        neg_words = negative_words(text, neg_hits) if neg_cat else []
        for name, code, market in stocks:
            if is_guest_stock(source, text, name, code):
                filt["他人事件误挂"] += 1
                continue
            base = {"name": name, "code": code, "market": market, "text": text[:160],
                    "full": text, "time": n.get("time", ""), "source": source}
            if pos_ok:
                if action == BOILER_DROP:
                    filt["套壳公告"] += 1
                elif action == BOILER_TO_NEG:
                    filt["套壳公告"] += 1
                    neg_records.append(dict(base, text=text[:160], neg_cat="减持/抛售",
                                            neg_words=[b_note], neg_level=1,
                                            neg_clause_note=b_note))
                elif level is not None:
                    if b_note:
                        filt["降级"] += 1
                    pos_records.append(dict(base, cat=cat, level=level, tier=tier,
                                            boilerplate=b_note))
            if neg_cat:
                clause = negative_clause(text, name, code, neg_words)
                if clause:      # 负面词需与该个股同处一句，且摘要直接显示该句
                    # 档位按「该个股所在分句」重新判定，而不是整条消息：汇总快讯
                    # （"新闻精选…公司新闻方面：①A拟减持 ④B被立案"）里别家公司的立案，
                    # 不能给本股定 N3 —— 30 日回测中这类串味把 N3 从 12 条 -5.24%/100%
                    # 稀释成 20 条 -2.31%/70.0%。
                    c_cat, c_hits = classify_negative(clause)
                    if c_cat:
                        neg_records.append(dict(base, text=clause[:160], neg_cat=c_cat,
                                                neg_words=negative_words(clause, c_hits),
                                                neg_level=judge_neg_level(clause, c_cat)))
    if any(filt.values()):
        print(f"[过滤] 套壳/程式化公告剔除 {filt['套壳公告']} 条，"
              f"已降级 {filt['降级']} 条，他人事件误挂剔除 {filt['他人事件误挂']} 条")

    # 去重 + 排序：利好先『订单落地』后『概念发酵』，同层级按评级高→低；
    # 利空按严重程度 N3→N1。同代码同类别同评级的重复消息只留一条。
    pos_records = dedup_sort(pos_records, lambda r: (r["code"], r["cat"], r["level"]),
                             lambda r: (0 if r["tier"] == TIER_LANDED else 1,
                                        -r["level"], r["time"]))
    neg_records = dedup_sort(neg_records, lambda r: (r["code"], r["neg_cat"], r["neg_level"]),
                             lambda r: (-r["neg_level"], r["time"]))

    filter_note = ("；已剔除套壳/程式化公告 %d 条、他人事件误挂 %d 条，"
                   "按规则降级 %d 条" % (filt["套壳公告"], filt["他人事件误挂"], filt["降级"])
                   ) if any(filt.values()) else ""

    # 3.4) 行情验证：给明细补 T日 / T+1 涨跌幅与相对基准指数的超额收益
    #      当日盘中（当日未收盘）时 T0 用实时快照现价，T+1 一律留空标『待验证』。
    #      行情接口失败只影响标注，绝不影响报告生成。
    quote_note = ""
    try:
        q_codes = [r["code"] for r in pos_records] + [r["code"] for r in neg_records]
        if q_codes:
            db = build_quote_db(q_codes)
            snap = None
            if not is_history:
                snap = fetch_snapshot(sorted({s for s in
                                              (sina_symbol(c) for c in q_codes) if s}))
            day_str, today_str = target.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
            annotate_quotes(pos_records, day_str, today_str, db, snap)
            stat = annotate_quotes(neg_records, day_str, today_str, db, snap)
            print(f"[行情] 已标注 {len(pos_records)}+{stat['total']} 条明细，"
                  f"其中 {sum(1 for r in pos_records if r.get('exc_t1') is not None)} 条拿到 T+1 超额")
    except Exception as e:
        quote_note = f"行情获取失败（{type(e).__name__}），明细标注『{VERIFY_NONE}』"
        print(f"[行情] {quote_note}")

    # 3.5) 回补模式：结构化落盘，供后续行情验证与规则回测直接读取
    if dump_cache:
        dump_backfill_cache(target, mode, day_news, pos_records, neg_records,
                            ok_sources, fail_sources, window_desc, filt=filt)

    # 4) 主线归纳（只统计提取到个股利好的消息，避免全量快讯把主线冲淡）
    theme_hits = {}
    for r in pos_records:
        th = pick_theme(r["full"])
        if th:
            theme_hits[th] = theme_hits.get(th, 0) + 1
    top_themes = sorted(theme_hits.items(), key=lambda x: -x[1])[:5]

    # 5) 报告文件（Markdown 与 HTML 各一份，内容一致）
    report_path, html_path = report_paths(report_date)
    pos_stats = build_stats(pos_records)
    neg_stats = build_stats(neg_records, is_negative=True)
    for builder, path in ((build_report, report_path), (build_html_report, html_path)):
        doc = builder(report_date, pos_records, neg_records, top_themes, ok_sources,
                      fail_sources, mode, news_count=len(day_news), window_desc=window_desc,
                      table_source=_STOCK_TABLE_SOURCE, filter_note=filter_note)
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)

    # 5.5) 通达信版面页（固定文件名，每次提取整体覆盖）
    tdx_path = tdx_page_path()
    with open(tdx_path, "w", encoding="utf-8") as f:
        f.write(build_tdx_page(report_date, pos_records, neg_records, ok_sources, fail_sources, mode))

    # 6) 历史记录（字段名与 show_history / GUI 读取保持一致）
    history = {"ts": now.strftime("%Y-%m-%d %H:%M:%S"), "mode": mode,
               "report_date": report_date.strftime("%Y-%m-%d"),
               "report_file": os.path.basename(report_path),
               "report_html": os.path.basename(html_path),
               "window": window_desc, "news_count": len(day_news),
               "stock_count": len(pos_records),
               "pos_landed": pos_stats["tier"][TIER_LANDED],
               "pos_concept": pos_stats["tier"][TIER_CONCEPT],
               "pos_l5": pos_stats["level"].get(5, 0),
               "neg_count": len(neg_records),
               "neg_n3": neg_stats["level"].get(3, 0),
               "sources_ok": ok_sources, "sources_fail": fail_sources, "status": "ok"}
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(history, ensure_ascii=False) + "\n")

    print(f"[完成] {now:%Y-%m-%d %H:%M:%S} 模式={mode} 数据日期={date_str} "
          f"消息{len(day_news)}条 利好{len(pos_records)}条"
          f"（{TIER_LANDED}{pos_stats['tier'][TIER_LANDED]} / {TIER_CONCEPT}"
          f"{pos_stats['tier'][TIER_CONCEPT]}，L5硬利好{pos_stats['level'].get(5, 0)}）"
          f" 利空{len(neg_records)}条（N3重大{neg_stats['level'].get(3, 0)}）")
    print(f"       Markdown -> {report_path}")
    print(f"       HTML     -> {html_path}")
    print(f"       通达信版面 -> {tdx_path}")
    return report_path


def _code_show(r):
    """代码显示：港股加 .HK 后缀，其余原样。"""
    return r["code"] + ".HK" if r["market"] == "HK" else r["code"]


def _merge_unique(lst, extras):
    """把 extras 中尚不在 lst 里的元素依次追加进 lst（保持顺序、去重），返回 lst。"""
    for x in extras:
        if x not in lst:
            lst.append(x)
    return lst


def prev_report_date(before):
    """早于 before 的最近一个已成功生成报告的数据日期，返回 date 或 None。"""
    if not os.path.exists(HISTORY_FILE):
        return None
    before_d = before.date() if hasattr(before, "date") else before
    latest = None
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    h = json.loads(line)
                except Exception:
                    continue
                if h.get("status") != "ok":
                    continue
                rd = h.get("report_date")
                if not rd:
                    continue
                try:
                    d = datetime.datetime.strptime(rd, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    continue
                if d < before_d and (latest is None or d > latest):
                    latest = d
    except Exception:
        pass
    return latest


# ============================= 交易日历判定（节假日/周末） =============================
# 用于「立即提取」按钮在节假日/周末动态切换为「多日聚合」。
# 周末(周六/日)由 weekday() 自动判为非交易日，无需在此列出；
# 这里只列出"工作日落在法定休市"的日期，格式 YYYY-MM-DD。
# 请按交易所实际休市日历核对/增删（本清单为示例，重点覆盖当前国庆假期）。
CN_TRADE_HOLIDAYS = frozenset({
    "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06",
    "2026-10-07", "2026-10-08",   # 国庆假期（工作日停市部分；10-03/04 周末已自动判休）
})

# 交易日历持久化：内置 CN_TRADE_HOLIDAYS 为兜底默认；用户在 GUI『维护交易日历』里
# 追加/修正的年份休市日写入 exe 同目录的 JSON 文件，每年手动更新一次即可。
TRADE_CALENDAR_FILE = os.path.join(BASE_DIR, "交易日历.json")
_TRADE_HOLIDAYS_CACHE = None


def load_trade_holidays():
    """内置默认 ∪ 用户 JSON 的并集（带内存缓存，保存后自动失效重读）。"""
    global _TRADE_HOLIDAYS_CACHE
    if _TRADE_HOLIDAYS_CACHE is not None:
        return _TRADE_HOLIDAYS_CACHE
    s = set(CN_TRADE_HOLIDAYS)
    if os.path.exists(TRADE_CALENDAR_FILE):
        try:
            with open(TRADE_CALENDAR_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                s.update(str(x).strip() for x in data if isinstance(x, str))
        except Exception as e:
            print(f"[交易日历] 读取 {os.path.basename(TRADE_CALENDAR_FILE)} 失败：{type(e).__name__}: {e}")
    _TRADE_HOLIDAYS_CACHE = s
    return s


def user_holidays():
    """返回用户 JSON 中维护的休市日列表（供 GUI 编辑显示）。"""
    if os.path.exists(TRADE_CALENDAR_FILE):
        try:
            with open(TRADE_CALENDAR_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return sorted({str(x).strip() for x in data if isinstance(x, str)})
        except Exception:
            pass
    return []


def save_trade_holidays(dates):
    """把用户维护的休市日写入 JSON 并刷新缓存。dates 为 YYYY-MM-DD 字符串可迭代。
    返回 None 成功；否则返回错误文本。"""
    global _TRADE_HOLIDAYS_CACHE
    clean = sorted({d.strip() for d in dates if d and len(d.strip()) == 10})
    try:
        with open(TRADE_CALENDAR_FILE, "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"写入交易日历失败：{type(e).__name__}: {e}"
    _TRADE_HOLIDAYS_CACHE = None
    load_trade_holidays()
    return None


def sync_trade_holidays_from_api(year, log=print, sleep_between=0.03):
    """自动同步某一年的交易日休市日历：逐个工作日请求 tool.bitefu.net/jiari，
    返回非 '0'（即 1=周末/2=法定节假日）视为休市。
    返回 (全年工作日休市日期列表, None)；中途失败返回 (None, 错误文本)。"""
    from urllib import request
    import time as _t
    fmt = "http://tool.bitefu.net/jiari/?d=%Y-%m-%d"
    d = datetime.date(year, 1, 1)
    end = datetime.date(year, 12, 31)
    closed = []
    step = 0
    while d <= end:
        if d.weekday() < 5:                      # 只查工作日（周一~五）
            q = d.strftime(fmt)
            try:
                r = request.urlopen(
                    request.Request(q, headers={"User-Agent": UA}), timeout=8
                ).read().decode("utf-8", "ignore").strip()
            except Exception as e:
                return None, f"同步中断于 {d}：{type(e).__name__}: {e}"
            if r != "0":
                closed.append(d.strftime("%Y-%m-%d"))
            step += 1
            if step % 50 == 0:
                log(f"[交易日历] 同步进度：已检查 {step} 个工作日…")
            _t.sleep(sleep_between)
        d += datetime.timedelta(days=1)
    log(f"[交易日历] 同步完成：全年共检测 {step} 个工作日，其中休市 {len(closed)} 天。")
    return closed, None


def is_trade_day(d):
    """是否交易日：周一~周五 且 不在（内置∪用户维护）休市清单中。"""
    dv = d.date() if hasattr(d, "date") else d
    if dv.weekday() >= 5:
        return False
    return dv.strftime("%Y-%m-%d") not in load_trade_holidays()


def holiday_break(today):
    """当前假期空档：从 today 往前找最近交易日，二者之间即假期。
    返回 (start, today, days) 元组；若 today 本身是交易日（非假期）返回 (None, today, 0)。"""
    d = today.date() if hasattr(today, "date") else today
    it = d
    for _ in range(40):
        if is_trade_day(it):
            if it == d:
                return None, d, 0
            return it + datetime.timedelta(days=1), d, (d - it).days
        it -= datetime.timedelta(days=1)
    return None, d, 0


def run_aggregate(start, end, mode="多日聚合", log=print):
    """多日聚合报告：把 [start, end] 区间内每天的提取结果（回补缓存）汇总成一份报告。

    节假日/周末一次运行即可把假期多天数据合成一份报告，供前端一次性导入。
    区间内缺缓存的日期会先按回补模式逐日抓取并落盘（复用 run_extract），保证聚合数据完整。
    返回聚合报告的 Markdown 路径；失败返回 None。"""
    start_d = start.date() if hasattr(start, "date") else start
    end_d = end.date() if hasattr(end, "date") else end
    if end_d < start_d:
        start_d, end_d = end_d, start_d
    n_days = (end_d - start_d).days + 1
    if n_days < 1:
        log("[聚合] 日期区间无效")
        return None
    os.makedirs(BACKFILL_DIR, exist_ok=True)

    # 1) 保证区间内每天都有结构化缓存（缺的按回补模式抓取落盘）
    for i in range(n_days):
        day = start_d + datetime.timedelta(days=i)
        d = datetime.datetime.combine(day, datetime.time(0, 0))
        if not os.path.exists(backfill_cache_path(d)):
            log(f"[聚合] 补齐 {day:%Y-%m-%d} 缓存（回补抓取）…")
            try:
                run_extract(d, mode="回补", dump_cache=True)
            except Exception as e:
                log(f"[聚合] {day:%Y-%m-%d} 抓取失败：{type(e).__name__}: {e}")

    # 2) 读取区间内全部缓存
    caches = []
    for i in range(n_days):
        day = start_d + datetime.timedelta(days=i)
        p = backfill_cache_path(day)
        if not os.path.exists(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                caches.append(json.load(f))
        except Exception as e:
            log(f"[聚合] 读取 {os.path.basename(p)} 失败：{type(e).__name__}: {e}")
    if not caches:
        log(f"[聚合] {start_d:%Y-%m-%d} ~ {end_d:%Y-%m-%d} 区间无任何有效缓存，无法生成聚合报告")
        return None

    # 3) 合并多日记录（利好/利空），去重排序与 run_extract 完全一致
    pos, neg = [], []
    ok_sources, fail_sources = [], []
    news_count = 0
    filt = {"套壳公告": 0, "他人事件误挂": 0, "降级": 0}
    for c in caches:
        pos += c.get("records") or []
        neg += c.get("neg_records") or []
        ok_sources = _merge_unique(ok_sources, c.get("sources_ok") or [])
        fail_sources = _merge_unique(fail_sources, c.get("sources_fail") or [])
        news_count += c.get("news_count", 0) or 0
        f = c.get("filter") or {}
        if isinstance(f, dict):
            for k in filt:
                filt[k] = filt.get(k, 0) + (f.get(k, 0) or 0)
    pos = dedup_sort(pos, lambda r: (r["code"], r["cat"], r["level"]),
                     lambda r: (0 if r["tier"] == TIER_LANDED else 1, -r["level"], r["time"]))
    neg = dedup_sort(neg, lambda r: (r["code"], r["neg_cat"], r["neg_level"]),
                     lambda r: (-r["neg_level"], r["time"]))

    filter_note = ("；已剔除套壳/程式化公告 %d 条、他人事件误挂 %d 条，按规则降级 %d 条"
                   % (filt["套壳公告"], filt["他人事件误挂"], filt["降级"])
                   ) if any(filt.values()) else ""

    # 4) 多日主线归纳（只统计提取到个股利好的消息）
    theme_hits = {}
    for r in pos:
        th = pick_theme(r["full"])
        if th:
            theme_hits[th] = theme_hits.get(th, 0) + 1
    top_themes = sorted(theme_hits.items(), key=lambda x: -x[1])[:5]

    # 5) 聚合窗口描述（多日）
    window_desc = f"{end_d:%Y-%m-%d} 多日聚合（{start_d:%m-%d} ~ {end_d:%m-%d}"
    if n_days > 1:
        window_desc += f"，涵盖 {n_days} 天"
    window_desc += "）"

    # 6) 渲染聚合 Markdown + HTML（以结束日命名，避免覆盖各单日报告）
    stem = f"{end_d:%Y%m%d}_个股利好聚合报告_{start_d:%Y%m%d}-{end_d:%Y%m%d}"
    agg_md = os.path.join(REPORT_DIR, stem + ".md")
    agg_html = os.path.join(REPORT_DIR, stem + ".html")
    pos_stats = build_stats(pos)
    neg_stats = build_stats(neg, is_negative=True)
    for builder, path in ((build_report, agg_md), (build_html_report, agg_html)):
        doc = builder(end_d, pos, neg, top_themes, ok_sources, fail_sources, mode,
                      news_count=news_count, window_desc=window_desc,
                      table_source=_STOCK_TABLE_SOURCE, filter_note=filter_note)
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)

    # 7) 历史记录（标记聚合区间，供前端/历史追溯）
    history = {"ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               "mode": mode, "report_date": end_d.strftime("%Y-%m-%d"),
               "report_file": os.path.basename(agg_md), "report_html": os.path.basename(agg_html),
               "window": window_desc, "news_count": news_count,
               "stock_count": len(pos), "pos_landed": pos_stats["tier"][TIER_LANDED],
               "pos_concept": pos_stats["tier"][TIER_CONCEPT],
               "pos_l5": pos_stats["level"].get(5, 0),
               "neg_count": len(neg), "neg_n3": neg_stats["level"].get(3, 0),
               "sources_ok": ok_sources, "sources_fail": fail_sources,
               "agg_start": start_d.strftime("%Y-%m-%d"), "agg_end": end_d.strftime("%Y-%m-%d"),
               "status": "ok"}
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(history, ensure_ascii=False) + "\n")

    log(f"[聚合完成] 聚合 {start_d:%Y-%m-%d} ~ {end_d:%Y-%m-%d}（{n_days} 天，模式={mode}）")
    log(f"           消息 {news_count} 条 利好 {len(pos)} 条（L5 {pos_stats['level'].get(5, 0)}）"
        f" 利空 {len(neg)} 条（N3 {neg_stats['level'].get(3, 0)}）")
    log(f"           Markdown -> {agg_md}")
    log(f"           HTML     -> {agg_html}")
    return agg_md


def build_report(report_date, records, neg_records, top_themes, ok_sources, fail_sources,
                 mode, news_count=0, window_desc="", table_source="", filter_note=""):
    """生成细化报告 markdown（利好五级 + 两层级，利空三级）。"""
    date_str = report_date.strftime("%Y-%m-%d")
    pos_stats = build_stats(records)
    neg_stats = build_stats(neg_records, is_negative=True)
    landed = [r for r in records if r["tier"] == TIER_LANDED]
    concept = [r for r in records if r["tier"] == TIER_CONCEPT]
    lines = [f"# {report_date.strftime('%Y年%m月%d日')} 个股利好消息细化报告",
             "",
             f"- **数据日期**：{date_str}",
             f"- **数据窗口**：{window_desc or date_str + ' 全天'}",
             f"- **生成方式**：{mode}提取（个股利好提取器 v{VERSION}，利好五级 + 利空三级 + 市场验证）",
             f"- **抓取来源**：{'、'.join(ok_sources) if ok_sources else '全部失败'}"
             + (f"；失败源：{'、'.join(fail_sources)}" if fail_sources else ""),
             f"- **识别范围**：{table_source or '脚本内置映射表'}",
             "- **市场验证**：T+1 相对基准指数（沪→上证指数 / 深北→深证综指）的超额收益，"
             "分档 强验证≥+3% / 弱验证+1~3% / 中性±1% / 背离-3~-1% / 显著背离≤-3%",
             f"- **统计**：窗口内消息 {news_count} 条；个股利好 {len(records)} 条"
             f"（{TIER_LANDED} {len(landed)} / {TIER_CONCEPT} {len(concept)}）；"
             f"个股利空 {len(neg_records)} 条（N3 重大 {neg_stats['level'].get(3, 0)}）"
             f"{filter_note}",
             ""]

    # 一、概览
    lines += ["## 一、跟踪概览", "", "| 利好评级 | 条数 |", "|---|---|"]
    for lv in (5, 4, 3, 2, 1):
        lines.append(f"| {LEVEL_NAME[lv]} | {pos_stats['level'].get(lv, 0)} |")
    lines += ["", "| 利空等级 | 条数 |", "|---|---|"]
    for lv in (3, 2, 1):
        lines.append(f"| {NEG_LEVEL_NAME[lv]} | {neg_stats['level'].get(lv, 0)} |")
    lines.append("")
    cat_cnt = {}
    for r in records:
        cat_cnt[r["cat"]] = cat_cnt.get(r["cat"], 0) + 1
    if cat_cnt:
        lines += ["**利好事件类别分布**", "", "| 类别 | 条数 |", "|---|---|"]
        for c, n in sorted(cat_cnt.items(), key=lambda x: -x[1]):
            lines.append(f"| {c} | {n} |")
        lines.append("")
    neg_cat_cnt = {}
    for r in neg_records:
        neg_cat_cnt[r["neg_cat"]] = neg_cat_cnt.get(r["neg_cat"], 0) + 1
    if neg_cat_cnt:
        lines += ["**利空事件类别分布**", "", "| 类别 | 条数 |", "|---|---|"]
        for c, n in sorted(neg_cat_cnt.items(), key=lambda x: -x[1]):
            lines.append(f"| {c} | {n} |")
        lines.append("")

    # 二、明细（利好，按类别分组，标注评级与层级）
    lines += ["## 二、个股利好明细", ""]
    if not records:
        lines.append("无。")
    else:
        for cat in [c for c, _ in CATEGORIES] + ["其他"]:
            sub = [r for r in records if r["cat"] == cat]
            if not sub:
                continue
            lines += [f"### {cat}", "",
                      "| 评级 | 层级 | 个股 | 代码 | 事件摘要 | T日 | T+1 | 超额(T+1) | 验证 | 来源 |",
                      "|---|---|---|---|---|---|---|---|---|---|"]
            for r in sub:
                text = r["text"].replace("|", "｜").replace("\n", " ")
                if len(text) > 90:
                    text = text[:90] + "…"
                t0, t1, exc, vfy = quote_cell(r)
                lines.append(f"| {LEVEL_NAME[r['level']]} | {r['tier']} | {r['name']} | "
                             f"{_code_show(r)} | {text} | {t0} | {t1} | {exc} | {vfy} | "
                             f"{r['source']} |")
            lines.append("")
    # 三、重点点评（按评级分层）
    lines += ["## 三、重点点评", ""]
    if not records:
        lines += ["无。", ""]
    for lv, desc in ((5, "订单/合同已落地、增持/回购/分红"),
                     (4, "量产/交付/获批/投产等产能资质落地")):
        sub = [r for r in records if r["level"] == lv]
        if sub:
            lines += [f"**{LEVEL_NAME[lv]}｜{desc}（可计入业绩预期）**：", ""]
            for r in sub[:8]:
                lines.append(f"- **{r['name']}（{_code_show(r)}）**：{r['text'][:70]}…")
            lines.append("")
    for lv, desc, note in ((3, "扩产投资/定增合资、拟回购拟增持", "属资本开支或未落地股东动作，兑现周期较长。"),
                           (2, "合作融资/经营改善/产品发布上线", "多处于新设公司/小批量/产能爬坡阶段，短期业绩弹性有限。"),
                           (1, "传闻/据悉/有望/拟/计划，未证实", "属传闻或计划类信息，需甄别，勿当落地利好。")):
        sub = [r for r in records if r["level"] == lv]
        if sub:
            names = "、".join(dict.fromkeys(r["name"] for r in sub[:10]))
            lines += [f"**{LEVEL_NAME[lv]}｜{desc}**：", "", f"- {names} 等，{note}", ""]

    # 四、市场验证汇总（用真实涨跌回看评级是否站得住）
    lines += ["## 四、市场验证汇总", ""]
    quoted = [r for r in records if r.get("exc_t1") is not None]
    if not quoted:
        lines += [f"暂无已收盘的 T+1 行情（明细均标『{VERIFY_NONE}』）。", ""]
    else:
        avg = sum(r["exc_t1"] for r in quoted) / len(quoted)
        win = sum(1 for r in quoted if r["exc_t1"] > 0) / len(quoted) * 100
        lines += [f"样本 {len(quoted)} 条（共 {len(records)} 条）："
                  f"平均超额 **{avg:+.2f}%**，超额胜率 **{win:.1f}%**。", ""]
        for title, key_fn in (("按评级", lambda r: LEVEL_NAME[r["level"]]),
                              ("按类别", lambda r: r["cat"]),
                              ("按层级", lambda r: r["tier"])):
            rows = verify_agg(records, key_fn)
            if not rows:
                continue
            lines += [f"**{title}**", "",
                      "| 分组 | 样本 | 平均超额 | 超额胜率 |", "|---|---:|---:|---:|"]
            for key, n, a, w in rows:
                lines.append(f"| {key} | {n} | {a:+.2f}% | {w:.1f}% |")
            lines.append("")

    # 五、主线
    lines += ["## 五、当日利好主线", ""]
    if top_themes:
        lines += ["1. " + "；".join(f"**{t}**（{c} 条）" for t, c in top_themes)]
    else:
        lines.append("当日主题分散，无显著主线。")
    lines.append("")

    # 五、利空跟踪（三级警示）
    lines += ["## 六、个股利空跟踪（三级警示）", ""]
    if not neg_records:
        lines += ["窗口内未提取到个股利空事件。", ""]
    else:
        for lv in (3, 2, 1):
            sub = [r for r in neg_records if r["neg_level"] == lv]
            if not sub:
                continue
            lines += [f"### {NEG_LEVEL_NAME[lv]}（{len(sub)} 条）", "",
                      "| 个股 | 代码 | 利空类别 | 事件摘要 | T日 | T+1 | 超额(T+1) | 验证 | 命中关键词 | 来源 |",
                      "|---|---|---|---|---|---|---|---|---|---|"]
            for r in sub:
                text = r["text"].replace("|", "｜").replace("\n", " ")
                if len(text) > 90:
                    text = text[:90] + "…"
                t0, t1, exc, vfy = quote_cell(r)
                lines.append(f"| {r['name']} | {_code_show(r)} | {r['neg_cat']} | {text} | "
                             f"{t0} | {t1} | {exc} | {vfy} | "
                             f"{'、'.join(r.get('neg_words') or [])} | {r['source']} |")
            lines.append("")

    # 六、风险
    lines += ["## 七、风险与甄别提示", "",
              "- 传闻/计划类信息未证实，需以公司公告为准；",
              "- 订单、框架协议类利好存在履约周期与兑现时点，短期业绩弹性有限；",
              "- 主题型利好（新设公司、小批量供货等）暂难计入业绩；",
              "- 利空明细只做规则归类，立案、处罚等事项以监管机构与公司公告为准；",
              "- 外部压制因素：美联储加息、美债收益率高位、日本央行加息等全球流动性变化；",
              "- 本报告基于公开快讯规则提取，可能存在遗漏或误分类，仅供信息参考。",
              ""]

    # 八、结论
    lines += ["## 八、结论", "",
              f"窗口内提取个股利好 {len(records)} 条（{TIER_LANDED} {len(landed)} 条、"
              f"{TIER_CONCEPT} {len(concept)} 条，其中 L5 硬利好 {pos_stats['level'].get(5, 0)} 条）；"
              f"个股利空 {len(neg_records)} 条（N3 重大 {neg_stats['level'].get(3, 0)} 条）。"
              f"建议按『订单落地』与『概念发酵』两个层级分别跟踪，利空标的优先规避。", ""]

    # 免责声明
    lines += ["---", "", "*免责声明：本报告由程序基于公开财经快讯自动整理，仅供信息参考，不构成任何投资建议。*", ""]

    # 九、代码清单（利好/利空分开，仅沪深主板）
    def _mb(seq):
        return sorted(set((r["code"], r["name"]) for r in seq
                          if is_main_board(r["code"], r["market"])))

    mb_landed, mb_concept, mb_neg = _mb(landed), _mb(concept), _mb(neg_records)
    lines += ["---", "", "## 九、代码清单（方便复制，仅沪深主板）", "",
              "> 已剔除 ST/*ST/退市、科创板(688)、创业板(300、301)、北交所、港股，仅保留沪深主板标的。", ""]
    for title, seq in ((f"利好·{TIER_LANDED}（{len(mb_landed)} 只）", mb_landed),
                       (f"利好·{TIER_CONCEPT}（{len(mb_concept)} 只）", mb_concept),
                       (f"利空（{len(mb_neg)} 只）", mb_neg)):
        lines += [f"**{title}**", "", "```"]
        lines += [code for code, _ in seq]
        lines += ["```", ""]
    if mb_landed or mb_concept or mb_neg:
        lines += ["**代码+名称对照表**", "", "| 代码 | 名称 | 类型 |", "|---|---|---|"]
        for code, name in mb_landed:
            lines.append(f"| {code} | {name} | 利好·{TIER_LANDED} |")
        for code, name in mb_concept:
            lines.append(f"| {code} | {name} | 利好·{TIER_CONCEPT} |")
        for code, name in mb_neg:
            lines.append(f"| {code} | {name} | 利空 |")
        lines.append("")
    return "\n".join(lines)


def report_paths(report_date):
    """返回该日期报告的两份文件路径 (markdown, html)。"""
    stem = report_date.strftime("%Y%m%d") + "_个股利好细化报告"
    return (os.path.join(REPORT_DIR, stem + ".md"),
            os.path.join(REPORT_DIR, stem + ".html"))


def tdx_page_path():
    """通达信版面页路径：固定文件名，每次提取整体覆盖，通达信只需指向这一个路径。"""
    return os.path.join(REPORT_DIR, "个股利好_通达信版面.html")


# 类别配色：沿用 A 股"利好=红"的视觉习惯，颜色越红表示级别越高
CAT_COLORS = {
    "订单/合同": "#d9251d",
    "增持/回购/分红": "#e0561f",
    "扩产/投资": "#c2410c",
    "技术/产品突破": "#b45309",
    "合作/合资/融资": "#9a6a1f",
    "经营改善": "#8a7d6d",
    "预期催化/传闻": "#6b7280",
    "其他": "#6b7280",
}
# 五级评级配色（利好＝暖色系）：正红 → 橙红 → 橙 → 琥珀 → 暖灰，越硬越浓
LEVEL_COLORS = {5: "#c0170c", 4: "#e2570f", 3: "#c8830a", 2: "#a1711d", 1: "#8a7d6d"}
# 三级利空配色（利空＝冷色系）：深蓝 → 蓝 → 蓝灰，与利好的暖色一眼分开
NEG_LEVEL_COLORS = {3: "#1e3a8a", 2: "#2563eb", 1: "#64748b"}
# 利空相关的浅色底（卡片/标签/代码chip），与 NEG_LEVEL_COLORS 同属冷色
NEG_TINT = {"bg": "#fbfcff", "line": "#d9e3f2", "line2": "#a9c2e8", "chip": "#eef3fd",
            "chip_line": "#c9d9f2", "text": "#1e3a8a"}

HTML_STYLE = """
:root{--red:#d9251d;--ink:#151a21;--ink2:#5d6775;--line:#e5e9f0;--bg:#eef1f6;--card:#fff;--amber:#b26a00}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:14px/1.75 "Microsoft YaHei","PingFang SC","Hiragino Sans GB",system-ui,sans-serif}
.wrap{max-width:1200px;margin:0 auto;padding:20px 18px 56px}
.hd{display:flex;justify-content:space-between;gap:16px;align-items:flex-end;
 background:linear-gradient(135deg,#1b2430,#2a3646);color:#fff;border-radius:14px;
 padding:20px 22px;box-shadow:0 6px 18px rgba(20,30,45,.18)}
.hd h1{margin:0 0 10px;font-size:22px;letter-spacing:.5px}
.meta{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);
 border-radius:999px;padding:3px 11px;font-size:12px;color:#dfe6f0}
.chip b{color:#ffcf4d;font-weight:600}
.hd-side{text-align:right;font-size:12px;color:#9fb0c6;white-space:nowrap}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:14px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;
 box-shadow:0 2px 8px rgba(20,30,45,.05)}
.kpi b{display:block;font-size:26px;line-height:1.2;font-family:Consolas,Menlo,monospace}
.kpi span{font-size:12px;color:var(--ink2)}
.kpi.hl b{color:var(--red)}
.kpi.neg b{color:#1e3a8a}
.kpi.neg{border-color:#d9e3f2;background:#fbfcff}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
 padding:16px 18px;margin:14px 0;box-shadow:0 2px 8px rgba(20,30,45,.05)}
.card h2{margin:0 0 12px;font-size:16px;padding-left:10px;border-left:4px solid var(--red)}
.hint{font-size:12px;color:var(--ink2);font-weight:400;margin-left:6px}
.bar-row{display:grid;grid-template-columns:130px 1fr 46px;align-items:center;gap:10px;margin:7px 0;font-size:13px}
.bar-track{background:#f0f3f8;border-radius:6px;height:12px;overflow:hidden}
.bar-track i{display:block;height:100%;border-radius:6px}
.bar-num{text-align:right;font-family:Consolas,monospace;color:var(--ink2)}
.toolbar{display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}
#kw{flex:1;min-width:240px;padding:8px 12px;border:1px solid var(--line);border-radius:8px;
 font-size:13px;outline:none;font-family:inherit}
#kw:focus{border-color:var(--red);box-shadow:0 0 0 3px rgba(217,37,29,.08)}
.fstat{font-size:12px;color:var(--ink2)}
.cat-block{margin-bottom:16px}
.cat-block h3{font-size:14px;margin:0 0 8px;padding-left:8px;border-left:3px solid var(--red)}
.cat-block h3 em{font-style:normal;font-size:11px;background:#f0f3f8;color:var(--ink2);
 border-radius:999px;padding:1px 8px;margin-left:6px}
.items{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:10px}
.item{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:#fcfdff}
.item:hover{border-color:#f0b4b0;box-shadow:0 3px 10px rgba(217,37,29,.08)}
.i-hd{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.nm{font-weight:700;font-size:14px;color:var(--red)}
.cd{font-family:Consolas,monospace;font-size:12px;background:#fdecea;color:#a81d16;
 border-radius:5px;padding:1px 7px}
.src{font-size:11px;color:#8792a3;margin-left:auto}
.i-tx{margin:0;font-size:12.5px;color:#3a4453;line-height:1.65}
.i-ft{font-size:11px;color:#98a3b3;margin-top:6px;font-family:Consolas,monospace}
.item[data-fold]{cursor:pointer}
.item[data-fold]:hover{background:#fff9f8}
.i-full{margin-top:8px;padding-top:8px;border-top:1px dashed var(--line);color:#3a4453;
 font-size:12.5px;line-height:1.75;white-space:pre-wrap;word-break:break-word}
.i-more{float:right;color:var(--red);font-size:11px;font-family:inherit}
.codes{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:12px}
.cc{font-family:Consolas,monospace;font-size:13px;background:#fdecea;color:#a81d16;
 border:1px solid #f6cfcb;border-radius:6px;padding:3px 10px}
.btn{border:none;border-radius:8px;padding:7px 14px;background:var(--red);color:#fff;
 font-size:13px;cursor:pointer;font-family:inherit}
.btn:hover{background:#c11d16}
.tbl{width:100%;border-collapse:collapse;font-size:13px}
.tbl th,.tbl td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}
.tbl th{background:#f7f9fc;color:var(--ink2);font-weight:600}
.tags{display:flex;flex-wrap:wrap;gap:8px}
.tag{background:#f7f9fc;border:1px solid var(--line);border-radius:999px;padding:4px 12px;font-size:13px}
.tag em{font-style:normal;color:var(--red);font-weight:700;margin-left:5px;font-family:Consolas,monospace}
.lst{margin:6px 0 12px;padding-left:20px}
.lst li{margin:5px 0;font-size:13px;color:#3a4453}
.lst li b{color:var(--red)}
.lst li .cd{margin:0 6px}
h4{font-size:13px;margin:10px 0 2px}
h4.t-hard{color:var(--red)}
h4.t-soft{color:var(--amber)}
h4.t-rumor{color:#6b7280}
.warn{border-left:4px solid var(--amber)}
.empty,.note{font-size:12.5px;color:#98a3b3;margin:0 0 10px}
.lv{display:inline-block;font-size:11px;font-weight:700;color:#fff;border-radius:5px;
 padding:1px 7px;letter-spacing:.3px;white-space:nowrap;font-family:Consolas,monospace}
.tier{font-size:11px;background:#f0f3f8;color:var(--ink2);border:1px solid var(--line);
 border-radius:999px;padding:1px 8px;white-space:nowrap}
.negcat{font-size:11px;background:#eef3fd;color:#1e3a8a;border:1px solid #c9d9f2;
 border-radius:5px;padding:1px 7px;white-space:nowrap}
.mt{font-size:11px;color:#98a3b3}
.card.negcard h2{border-left-color:#1e3a8a}
.item.neg{background:#fbfcff;border-color:#d9e3f2}
.item.neg:hover{border-color:#a9c2e8;box-shadow:0 3px 10px rgba(30,58,138,.08)}
.item.neg .nm{color:#1e3a8a}
.item.neg .cd{background:#eef3fd;color:#1e3a8a}
.item.neg .i-more{color:#2563eb}
.codes.neg .cc{background:#eef3fd;color:#1e3a8a;border-color:#c9d9f2}
.clh{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:12px 0 6px}
.clh h4{margin:0;font-size:13px;color:var(--ink)}
.lgd{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 12px}
.lgd span{font-size:11.5px;color:var(--ink2);display:inline-flex;align-items:center;gap:5px}
.lgd i{display:inline-block;width:10px;height:10px;border-radius:3px}
footer{margin-top:18px;text-align:center;font-size:12px;color:#93a0b0}
.i-q{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:6px 0 0;font-size:11.5px;color:var(--ink2)}
.qv{border-radius:5px;padding:1px 7px;font-size:11px;color:#fff;white-space:nowrap}
.qtab{width:100%;border-collapse:collapse;font-size:12px;margin:4px 0 12px}
.qtab th,.qtab td{border-bottom:1px solid #eef1f5;padding:4px 6px;text-align:right}
.qtab th:first-child,.qtab td:first-child{text-align:left}
.qtab thead th{color:var(--ink2);font-weight:600;border-bottom:1px solid #dfe4ea}
@media(max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}
 .hd{flex-direction:column;align-items:flex-start}.hd-side{text-align:left}}
"""

HTML_SCRIPT = """
function toggleItem(it){
  var full=it.querySelector('.i-full');
  if(!full)return;
  var tag=it.querySelector('.i-more'), open=full.hasAttribute('hidden');
  if(open){full.removeAttribute('hidden');}else{full.setAttribute('hidden','');}
  if(tag)tag.textContent=open?'点击收起':'点击展开全文';
}
document.addEventListener('click',function(e){
  var it=e.target.closest?e.target.closest('.item'):null;
  if(it&&it.getAttribute('data-fold'))toggleItem(it);
});
function applyFilter(){
  var kw=(document.getElementById('kw').value||'').trim().toLowerCase();
  var items=document.querySelectorAll('.item'), hit=0, i;
  for(i=0;i<items.length;i++){
    var ok=!kw||(items[i].getAttribute('data-kw')||'').indexOf(kw)>=0;
    items[i].style.display=ok?'':'none';
    if(ok)hit++;
  }
  var blocks=document.querySelectorAll('.cat-block'), j, k;
  for(j=0;j<blocks.length;j++){
    var sub=blocks[j].querySelectorAll('.item'), vis=0;
    for(k=0;k<sub.length;k++){if(sub[k].style.display!=='none')vis++;}
    blocks[j].style.display=vis?'':'none';
  }
  document.getElementById('fstat').textContent=kw?('命中 '+hit+' 条'):('');
}
function copyCodes(btn,listId){
  var nodes=document.querySelectorAll('#'+listId+' .cc'), arr=[], i;
  for(i=0;i<nodes.length;i++)arr.push(nodes[i].textContent.trim());
  if(!arr.length)return;
  var txt=arr.join('\\r\\n'), ta=document.createElement('textarea'), ok=false;
  ta.value=txt;ta.style.position='fixed';ta.style.left='-9999px';
  document.body.appendChild(ta);ta.select();
  try{ok=document.execCommand('copy');}catch(e){ok=false;}
  document.body.removeChild(ta);
  if(!ok&&navigator.clipboard){navigator.clipboard.writeText(txt);ok=true;}
  var old=btn.textContent;
  btn.textContent=ok?('已复制 '+arr.length+' 只'):'复制失败，请手动选择';
  setTimeout(function(){btn.textContent=old;},1600);
}
"""


def lv_badge(level):
    """利好评级徽章（L5 最红 → L1 灰）。"""
    c = LEVEL_COLORS.get(level, "#6b7280")
    return f'<span class="lv" style="background:{c}">{LEVEL_NAME.get(level, "L?")}</span>'


def neg_badge(neg_level):
    """利空等级徽章（N3 深红 → N1 灰红）。"""
    c = NEG_LEVEL_COLORS.get(neg_level, "#a1756f")
    return f'<span class="lv" style="background:{c}">{NEG_LEVEL_NAME.get(neg_level, "N?")}</span>'


def legend(levels, colors, names):
    """评级图例。"""
    return ('<div class="lgd">' + "".join(
        f'<span><i style="background:{colors[lv]}"></i>{names[lv]}</span>' for lv in levels)
        + "</div>")


def build_html_report(report_date, records, neg_records, top_themes, ok_sources, fail_sources,
                      mode, news_count=0, window_desc="", table_source="", filter_note=""):
    """生成单文件 HTML 报告：利好五级/两层级 + 利空三级，
    样式与脚本全部内联，无任何外部依赖，双击即可用浏览器打开。"""
    esc = html.escape
    date_str = report_date.strftime("%Y-%m-%d")
    title = report_date.strftime("%Y年%m月%d日") + " 个股利好消息细化报告"
    gen_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    pos_stats = build_stats(records)
    neg_stats = build_stats(neg_records, is_negative=True)
    landed = [r for r in records if r["tier"] == TIER_LANDED]
    concept = [r for r in records if r["tier"] == TIER_CONCEPT]

    cat_cnt = {}
    for r in records:
        cat_cnt[r["cat"]] = cat_cnt.get(r["cat"], 0) + 1
    neg_cat_cnt = {}
    for r in neg_records:
        neg_cat_cnt[r["neg_cat"]] = neg_cat_cnt.get(r["neg_cat"], 0) + 1

    def _mb(seq):
        return sorted(set((r["code"], r["name"]) for r in seq
                          if is_main_board(r["code"], r["market"])))

    mb_landed, mb_concept, mb_neg = _mb(landed), _mb(concept), _mb(neg_records)

    def code_show(r):
        return r["code"] + ".HK" if r["market"] == "HK" else r["code"]

    src_txt = "、".join(ok_sources) if ok_sources else "全部失败"
    if fail_sources:
        src_txt += f"（失败源：{'、'.join(fail_sources)}）"

    p = ['<!DOCTYPE html>', '<html lang="zh-CN">', '<head>',
         '<meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         f"<title>{esc(title)}</title>", "<style>" + HTML_STYLE + "</style>",
         "</head>", "<body>", '<div class="wrap">']

    # 头部
    p += ['<header class="hd"><div>', f"<h1>{esc(title)}</h1>", '<div class="meta">',
          f'<span class="chip">数据日期 <b>{date_str}</b></span>',
          f'<span class="chip">数据窗口 <b>{esc(window_desc or date_str + " 全天")}</b></span>',
          f'<span class="chip">抓取来源 <b>{esc(src_txt)}</b></span>',
          f'<span class="chip">识别范围 <b>{esc(table_source or "脚本内置映射表")}</b></span>',
          (f'<span class="chip">过滤 <b>{esc(filter_note.lstrip("；"))}</b></span>'
           if filter_note else ""),
          "</div></div>",
          f'<div class="hd-side">{esc(mode)}提取 · v{VERSION}<br>{gen_time}</div>',
          "</header>"]

    # KPI（利好 + 利空双轨）
    p += ['<section class="kpis">',
          f'<div class="kpi"><b>{news_count}</b><span>窗口内消息</span></div>',
          f'<div class="kpi hl"><b>{len(records)}</b><span>个股利好</span></div>',
          f'<div class="kpi hl"><b>{pos_stats["level"].get(5, 0)}</b><span>L5 硬利好</span></div>',
          f'<div class="kpi hl"><b>{len(landed)}</b><span>订单落地</span></div>',
          f'<div class="kpi neg"><b>{len(neg_records)}</b><span>个股利空</span></div>',
          f'<div class="kpi neg"><b>{neg_stats["level"].get(3, 0)}</b><span>N3 重大利空</span></div>',
          "</section>"]

    # 一、跟踪概览
    p += ['<section class="card"><h2>一、跟踪概览'
          f'<span class="hint">利好 {len(records)} 条 · 利空 {len(neg_records)} 条</span></h2>']
    p.append(legend((5, 4, 3, 2, 1), LEVEL_COLORS, LEVEL_NAME))
    if records:
        top_lv = max([pos_stats["level"].get(l, 0) for l in (5, 4, 3, 2, 1)] + [1])
        p.append('<div class="bars">')
        for lv in (5, 4, 3, 2, 1):
            n = pos_stats["level"].get(lv, 0)
            p.append(f'<div class="bar-row"><span>{lv_badge(lv)}</span>'
                     f'<span class="bar-track"><i style="width:{max(2, int(n / top_lv * 100))}%;'
                     f'background:{LEVEL_COLORS[lv]}"></i></span>'
                     f'<span class="bar-num">{n}</span></div>')
        p.append("</div>")
        p.append('<div class="tags">'
                 f'<span class="tag">{TIER_LANDED}<em>{len(landed)}</em></span>'
                 f'<span class="tag">{TIER_CONCEPT}<em>{len(concept)}</em></span></div>')
    else:
        p.append('<p class="empty">窗口内未提取到符合条件的个股利好。</p>')
    if cat_cnt:
        top = max(cat_cnt.values())
        p.append('<h4>利好事件类别分布</h4><div class="bars">')
        for c, n in sorted(cat_cnt.items(), key=lambda x: -x[1]):
            p.append(f'<div class="bar-row"><span>{esc(c)}</span>'
                     f'<span class="bar-track"><i style="width:{max(4, int(n / top * 100))}%;'
                     f'background:{CAT_COLORS.get(c, "#6b7280")}"></i></span>'
                     f'<span class="bar-num">{n}</span></div>')
        p.append("</div>")
    if neg_cat_cnt:
        top = max(neg_cat_cnt.values())
        p.append('<h4>利空事件类别分布</h4><div class="bars">')
        for c, n in sorted(neg_cat_cnt.items(), key=lambda x: -x[1]):
            p.append(f'<div class="bar-row"><span>{esc(c)}</span>'
                     f'<span class="bar-track"><i style="width:{max(4, int(n / top * 100))}%;'
                     f'background:{NEG_LEVEL_COLORS.get(NEG_LEVEL.get(c, 1), "#a1756f")}"></i></span>'
                     f'<span class="bar-num">{n}</span></div>')
        p.append("</div>")
    p.append("</section>")

    # 二、明细（利好按类别分组，标注评级与层级）
    p += ['<section class="card"><h2>二、个股利好明细'
          f'<span class="hint">共 {len(records)} 条</span></h2>']
    if records or neg_records:
        p += ['<div class="toolbar"><input id="kw" type="search" oninput="applyFilter()" '
              'placeholder="过滤：股票名称 / 代码 / L5 / N3 / 关键词（同时作用于利好与利空）">'
              '<span id="fstat" class="fstat"></span></div>']
    for cat in [c for c, _ in CATEGORIES] + ["其他"]:
        sub = [r for r in records if r["cat"] == cat]
        if not sub:
            continue
        p.append(f'<div class="cat-block"><h3 style="border-color:{CAT_COLORS.get(cat, "#6b7280")}">'
                 f'{esc(cat)}<em>{len(sub)}</em></h3><div class="items">')
        for r in sub:
            kw = esc((r["name"] + " " + r["code"] + " " + r["text"] + " "
                      + LEVEL_NAME[r["level"]] + " " + r["tier"]).lower())
            full = r.get("full") or r["text"]
            cut = len(full) > len(r["text"])
            p += [f'<article class="item" data-kw="{kw}"' + (" data-fold='1'" if cut else "") + ">",
                  '<div class="i-hd">'
                  f'{lv_badge(r["level"])}'
                  f'<span class="nm">{esc(r["name"])}</span>'
                  f'<span class="cd">{esc(code_show(r))}</span>'
                  f'<span class="src">{esc(r["source"])}</span></div>']
            t0, t1, exc, vfy = quote_cell(r)
            p.append(f'<div class="i-q"><span class="qv" '
                     f'style="background:{VERIFY_COLORS.get(vfy, "#9ca3af")}">{esc(vfy)}</span>'
                     f'<span>T日 <b>{t0}</b></span><span>T+1 <b>{t1}</b></span>'
                     f'<span>超额 <b>{exc}</b></span></div>')
            p += [f'<p class="i-tx">{esc(r["text"])}{"…" if cut else ""}</p>']
            if cut:
                p.append(f'<div class="i-full" hidden>{esc(full)}</div>')
            p.append('<div class="i-ft">'
                     f'<span class="tier">{esc(r["tier"])}</span> {esc(r.get("time") or "")}'
                     + ('<span class="i-more">点击展开全文</span>' if cut else "")
                     + "</div>")
            p.append("</article>")
        p.append("</div></div>")
    if not records:
        p.append('<p class="empty">无。</p>')
    p.append("</section>")

    # 三、重点点评（按五级评级分层）
    p += ['<section class="card"><h2>三、重点点评'
          '<span class="hint">按五级评级分层</span></h2>']
    if not records:
        p.append('<p class="empty">无。</p>')
    for lv, head, note in ((5, "订单/合同已落地、增持/回购/分红", "可计入业绩与股东回报预期"),
                           (4, "量产/交付/获批/投产等产能资质落地", "准硬利好，重点看产能释放节奏"),
                           (3, "扩产投资/定增合资、拟回购拟增持", "资本开支或未落地股东动作，兑现周期较长"),
                           (2, "合作融资/经营改善/产品发布上线", "多处于新设公司/小批量/产能爬坡阶段，短期业绩弹性有限"),
                           (1, "传闻/据悉/有望/拟/计划，未证实", "属传闻或计划类信息，需甄别，勿当落地利好")):
        sub = [r for r in records if r["level"] == lv]
        if not sub:
            continue
        cls = "t-hard" if lv >= 4 else ("t-soft" if lv >= 2 else "t-rumor")
        p.append(f'<h4 class="{cls}">{lv_badge(lv)} {esc(head)}（{len(sub)} 条）</h4>')
        if lv >= 4:
            p.append('<ul class="lst">')
            for r in sub[:8]:
                p.append(f'<li><b>{esc(r["name"])}</b><span class="cd">{esc(code_show(r))}</span>'
                         f'{esc(r["text"][:80])}…</li>')
            p.append("</ul>")
        else:
            names = "、".join(dict.fromkeys(r["name"] for r in sub[:10]))
            p.append(f'<p class="note">{esc(names)} 等，{esc(note)}。</p>')
    p.append("</section>")

    # 四、市场验证汇总：用真实涨跌回看评级/类别/层级是否站得住
    quoted = [r for r in records if r.get("exc_t1") is not None]
    p += ['<section class="card"><h2>四、市场验证汇总'
          f'<span class="hint">T+1 相对基准超额 · 样本 {len(quoted)}/{len(records)}</span></h2>']
    if quoted:
        avg = sum(r["exc_t1"] for r in quoted) / len(quoted)
        win = sum(1 for r in quoted if r["exc_t1"] > 0) / len(quoted) * 100
        p.append(f'<p class="mt">平均超额 <b>{avg:+.2f}%</b> · 超额胜率 <b>{win:.1f}%</b>'
                 '　分档：强验证≥+3% / 弱验证+1~3% / 中性±1% / 背离-3~-1% / 显著背离≤-3%</p>')
        for qtitle, key_fn in (("按评级", lambda r: LEVEL_NAME[r["level"]]),
                               ("按类别", lambda r: r["cat"]),
                               ("按层级", lambda r: r["tier"])):
            rows = verify_agg(records, key_fn)
            if not rows:
                continue
            p.append('<table class="qtab"><thead><tr>'
                     f'<th>{qtitle}</th><th>样本</th><th>平均超额</th><th>超额胜率</th>'
                     '</tr></thead><tbody>')
            for key, n, a, w in rows:
                col = "#c81e12" if a > 0 else ("#2e7d32" if a < 0 else "#6b7280")
                p.append(f'<tr><td>{esc(str(key))}</td><td>{n}</td>'
                         f'<td style="color:{col}">{a:+.2f}%</td><td>{w:.1f}%</td></tr>')
            p.append("</tbody></table>")
    else:
        p.append('<p class="mt">本次未取到 T+1 行情（行情接口失败，或 T+1 尚未收盘），'
                 '暂无法做市场验证；接口恢复后重新提取即可。</p>')
    p.append("</section>")

    # 五、主线
    p += ['<section class="card"><h2>五、当日利好主线'
          '<span class="hint">只统计提取到个股利好的消息</span></h2>']
    if top_themes:
        p.append('<div class="tags">')
        for t, c in top_themes:
            p.append(f'<span class="tag">{esc(t)}<em>{c}</em></span>')
        p.append("</div>")
    else:
        p.append('<p class="empty">当日主题分散，无显著主线。</p>')
    p.append("</section>")

    # 五、利空跟踪（三级警示）
    p += ['<section class="card negcard"><h2>六、个股利空跟踪（三级警示）'
          f'<span class="hint">共 {len(neg_records)} 条</span></h2>']
    p.append(legend((3, 2, 1), NEG_LEVEL_COLORS, NEG_LEVEL_NAME))
    if neg_records:
        top_n = max([neg_stats["level"].get(l, 0) for l in (3, 2, 1)] + [1])
        p.append('<div class="bars">')
        for lv in (3, 2, 1):
            n = neg_stats["level"].get(lv, 0)
            p.append(f'<div class="bar-row"><span>{neg_badge(lv)}</span>'
                     f'<span class="bar-track"><i style="width:{max(2, int(n / top_n * 100))}%;'
                     f'background:{NEG_LEVEL_COLORS[lv]}"></i></span>'
                     f'<span class="bar-num">{n}</span></div>')
        p.append("</div>")
        for lv in (3, 2, 1):
            sub = [r for r in neg_records if r["neg_level"] == lv]
            if not sub:
                continue
            p.append(f'<div class="cat-block"><h3 style="border-color:{NEG_LEVEL_COLORS[lv]}">'
                     f'{NEG_LEVEL_NAME[lv]}<em>{len(sub)}</em></h3><div class="items">')
            for r in sub:
                kw = esc((r["name"] + " " + r["code"] + " " + r["text"] + " "
                          + r["neg_cat"] + " " + NEG_LEVEL_NAME[lv]).lower())
                full = r.get("full") or r["text"]
                cut = len(full) > len(r["text"])
                p += [f'<article class="item neg" data-kw="{kw}"'
                      + (" data-fold='1'" if cut else "") + ">",
                      '<div class="i-hd">'
                      f'{neg_badge(r["neg_level"])}'
                      f'<span class="nm">{esc(r["name"])}</span>'
                      f'<span class="cd">{esc(code_show(r))}</span>'
                      f'<span class="src">{esc(r["source"])}</span></div>',
                      f'<p class="i-tx"><span class="negcat">{esc(r["neg_cat"])}</span> '
                      f'{esc(r["text"])}{"…" if cut else ""}</p>']
                t0, t1, exc, vfy = quote_cell(r)       # 利空同样标注真实涨跌，便于回看是否兑现
                p.append(f'<div class="i-q"><span class="qv" '
                         f'style="background:{VERIFY_COLORS.get(vfy, "#9ca3af")}">{esc(vfy)}</span>'
                         f'<span>T日 <b>{t0}</b></span><span>T+1 <b>{t1}</b></span>'
                         f'<span>超额 <b>{exc}</b></span></div>')
                if cut:
                    p.append(f'<div class="i-full" hidden>{esc(full)}</div>')
                p.append('<div class="i-ft">'
                         + "、".join(esc(h) for h in (r.get("neg_words") or []))
                         + f' · {esc(r.get("time") or "")}'
                         + ('<span class="i-more">点击展开全文</span>' if cut else "")
                         + "</div>")
                p.append("</article>")
            p.append("</div></div>")
    else:
        p.append('<p class="empty">窗口内未提取到个股利空事件。</p>')
    p.append("</section>")

    # 六、风险
    p += ['<section class="card warn"><h2>七、风险与甄别提示</h2><ul class="lst">',
          "<li>传闻/计划类信息未证实，需以公司公告为准；</li>",
          "<li>订单、框架协议类利好存在履约周期与兑现时点，短期业绩弹性有限；</li>",
          "<li>主题型利好（新设公司、小批量供货等）暂难计入业绩；</li>",
          "<li>利空明细只做规则归类，立案、处罚等事项以监管机构与公司公告为准；</li>",
          "<li>外部压制因素：美联储加息、美债收益率高位、日本央行加息等全球流动性变化；</li>",
          "<li>本报告基于公开财经快讯规则提取，可能存在遗漏或误分类，仅供信息参考。</li>",
          "</ul></section>"]

    # 七、结论
    p += ['<section class="card"><h2>八、结论</h2>',
          f"<p>窗口内提取个股利好 <b>{len(records)}</b> 条（{TIER_LANDED} <b>{len(landed)}</b> 条、"
          f"{TIER_CONCEPT} <b>{len(concept)}</b> 条，其中 L5 硬利好 "
          f"<b>{pos_stats['level'].get(5, 0)}</b> 条）；个股利空 <b>{len(neg_records)}</b> 条"
          f"（N3 重大 <b>{neg_stats['level'].get(3, 0)}</b> 条）。"
          f"建议按『订单落地』与『概念发酵』两个层级分别跟踪，利空标的优先规避。</p></section>"]

    # 八、代码清单（利好/利空分开，各自一键复制，仅沪深主板）
    p += ['<section class="card"><h2>九、代码清单（仅沪深主板）</h2>',
          '<p class="note">已剔除 ST/*ST/退市、科创板(688)、创业板(300、301)、北交所、港股，'
          '只保留沪深主板标的，便于直接复制。</p>']
    for bid, cid, name, seq, is_neg in (
            ("btn-landed", "code-landed", f"利好·{TIER_LANDED}（{len(mb_landed)} 只）", mb_landed, False),
            ("btn-concept", "code-concept", f"利好·{TIER_CONCEPT}（{len(mb_concept)} 只）", mb_concept, False),
            ("btn-neg", "code-neg", f"利空（{len(mb_neg)} 只）", mb_neg, True)):
        btn_style = ' style="background:#1e3a8a"' if is_neg else ""
        p.append(f'<div class="clh"><h4>{esc(name)}</h4>'
                 f'<button id="{bid}" class="btn"{btn_style} '
                 f"onclick=\"copyCodes(this,'{cid}')\">一键复制</button></div>")
        p.append(f'<div id="{cid}" class="codes{" neg" if is_neg else ""}">')
        for code, nm in seq:
            p.append(f'<span class="cc" title="{esc(nm)}">{esc(code)}</span>')
        p.append("</div>")
    if mb_landed or mb_concept or mb_neg:
        p.append('<table class="tbl"><thead><tr><th>代码</th><th>名称</th><th>类型</th>'
                 "</tr></thead><tbody>")
        for code, nm in mb_landed:
            p.append(f'<tr><td class="cd">{esc(code)}</td><td>{esc(nm)}</td>'
                     f"<td>利好·{TIER_LANDED}</td></tr>")
        for code, nm in mb_concept:
            p.append(f'<tr><td class="cd">{esc(code)}</td><td>{esc(nm)}</td>'
                     f"<td>利好·{TIER_CONCEPT}</td></tr>")
        for code, nm in mb_neg:
            p.append(f'<tr><td class="cd">{esc(code)}</td><td>{esc(nm)}</td><td>利空</td></tr>')
        p.append("</tbody></table>")
    p.append("</section>")

    p += ["<footer>本报告由程序基于公开财经快讯自动整理，仅供信息参考，不构成任何投资建议。"
          f"<br>生成时间：{gen_time}　·　个股利好提取器 v{VERSION}（利好五级 + 利空三级 + 市场验证）</footer>",
          "</div>", "<script>" + HTML_SCRIPT + "</script>", "</body>", "</html>"]
    return "\n".join(p)


# 通达信版面页样式：紧凑列表式，无任何外部依赖（通达信内嵌浏览器可直接渲染）。
TDX_STYLE = """
*{box-sizing:border-box}
body{margin:0;background:#f4f5f7;color:#1f2329;
     font:13px/1.5 "Microsoft YaHei","微软雅黑",Arial,sans-serif}
.wrap{padding:8px 10px 18px}
.hd{display:flex;align-items:baseline;flex-wrap:wrap;gap:8px;padding:6px 2px 8px}
.hd h1{margin:0;font-size:16px;font-weight:700}
.hd .meta{color:#5b6472;font-size:12px}
.hd .meta b{color:#c81e12}
.side{margin-left:auto;display:flex;align-items:center;gap:8px}
.hint{color:#8a93a0;font-size:11px}
.btn{border:0;background:#c81e12;color:#fff;font-size:11.5px;font-weight:700;
     padding:3px 9px;border-radius:4px;cursor:pointer;white-space:nowrap}
.btn:hover{background:#a9170e}
.btn.neg{background:#1e3a8a}
.btn.neg:hover{background:#152a63}
.btns{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 2px 4px}
.bl{font-size:11.5px;color:#8a93a0}
.list{background:#fff;border:1px solid #e3e6eb;border-radius:6px;overflow:hidden}
.row{display:flex;align-items:center;gap:8px;padding:4px 8px;border-top:1px solid #eef0f3}
.row:first-child{border-top:0}
.row:hover{background:#fff8f2}
.head-row{background:#f7f8fa;color:#5b6472;font-size:12px;font-weight:700}
.head-row:hover{background:#f7f8fa}
.lv{flex:0 0 26px;text-align:center;color:#fff;border-radius:3px;font-size:11px;
    line-height:17px;font-weight:700}
.code{flex:0 0 132px;font-family:Consolas,monospace;font-size:12.5px;white-space:nowrap;
      overflow:hidden;text-overflow:ellipsis}
.code a{color:#1d70b8;text-decoration:none}
.code a:hover{text-decoration:underline}
.code .hk{color:#5b6472}
.tier{flex:0 0 62px;color:#5b6472;font-size:11.5px;white-space:nowrap}
.txt{flex:1 1 auto;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#333a44}
.pc{flex:0 0 62px;text-align:left;font-family:Consolas,monospace;font-size:12.5px;font-weight:700}
.up{color:#c81e12}.down{color:#12833b}.flat{color:#9ca3af}
.cat{flex:0 0 74px;color:#8a93a0;font-size:11.5px;white-space:nowrap;overflow:hidden;
     text-overflow:ellipsis}
.empty{padding:16px;color:#8a93a0}
.sect{margin:12px 2px 6px;font-size:13.5px;font-weight:700;color:#1e3a8a;
      border-left:3px solid #1e3a8a;padding-left:7px}
.sect span{font-weight:400;color:#5b6472;font-size:12px}
.list.neg{background:#fbfcff;border-color:#d9e3f2}
.list.neg .row{border-top-color:#eaf0fa}
.list.neg .row:hover{background:#f2f7ff}
footer{padding:10px 2px;color:#9ca3af;font-size:11px}
"""


def build_tdx_page(report_date, records, neg_records, ok_sources, fail_sources, mode):
    """生成『通达信版面』单文件 HTML：固定文件名、每次提取整体覆盖。
    列表式（档位 + 当日行情 + 代码名称 + 层级 + 摘要），利好暖色 / 利空冷色，
    末尾附『利空警示』块；每档一个『加入通达信板块』按钮；
    点代码走通达信内部伪 URL http://www.treeid/code_XXXXXX
    直接跳到该股 —— 与 D:\\new_tdx\\company 下现成自定义网页同一套写法。"""
    esc = html.escape
    date_str = report_date.strftime("%Y-%m-%d")
    gen_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    pos_stats = build_stats(records)
    neg_stats = build_stats(neg_records, is_negative=True)
    quoted = [r for r in records if r.get("pct_t0") is not None]

    def _row(r, badge_html, mid, cat):
        """一行：档位徽章 + 当日行情 + 代码名称（可点跳通达信）+ 层级/类别 + 摘要。"""
        code = r["code"]
        label = f'{code} {r["name"]}'
        if r["market"] != "HK" and re.match(r"^\d{6}$", code):
            cell = (f'<a href="http://www.treeid/code_{code}" '
                    f'title="点击跳转通达信：{esc(r["name"])}">{esc(label)}</a>')
        else:
            cell = f'<span class="hk">{esc(label)}</span>'
        pct = r.get("pct_t0")
        cls = "up" if (pct or 0) > 0 else ("down" if pct is not None else "flat")
        return (f'<div class="row">{badge_html}'
                f'<span class="pc {cls}">{fmt_pct(pct)}</span>'
                f'<span class="code">{cell}</span>'
                f'<span class="tier">{esc(mid)}</span>'
                f'<span class="cat">{esc(cat)}</span>'
                f'<span class="txt" title="{esc(r.get("full") or r["text"])}">{esc(r["text"])}</span></div>')

    # 排序：评级降序 -> 订单落地优先 -> 当日涨幅降序（无行情的排最后）
    def _key(r):
        pct = r.get("pct_t0")
        return (-r["level"], 0 if r["tier"] == TIER_LANDED else 1,
                -(pct if pct is not None else -999))

    def _payload(rows):
        """拼成通达信 AddToBlock_ 协议串（6→1 沪市、4/8→2 北交所、其余 0 深市），按代码去重。"""
        out, seen = [], set()
        for r in rows:
            code = r["code"]
            if r["market"] == "HK" or not re.match(r"^\d{6}$", code) or code in seen:
                continue
            seen.add(code)
            out.append(f"{'1' if code[0] == '6' else ('2' if code[0] in '48' else '0')}#{code}")
        return "|".join(out)

    def _main_codes(rows):
        return {r["code"] for r in rows
                if r["market"] != "HK" and re.match(r"^\d{6}$", r["code"])}

    # 分级按钮：利好 全部/L5~L1；利空 全部/N3~N1；每组独立去重、各自一条协议串
    blk_groups = {}
    for gid, rows in ([("pos", records)] +
                      [(f"l{lv}", [r for r in records if r["level"] == lv])
                       for lv in (5, 4, 3, 2, 1)] +
                      [("neg", neg_records)] +
                      [(f"n{lv}", [r for r in neg_records if r["neg_level"] == lv])
                       for lv in (3, 2, 1)]):
        payload = _payload(rows)
        if payload:
            blk_groups[gid] = payload

    def _blk_bar(kind):
        """档位细分按钮栏：利好暖色、利空冷色，每组一个按钮。"""
        if kind == "pos":
            specs = [("pos", "全部利好", records)] + \
                    [(f"l{lv}", f"L{lv}", [r for r in records if r["level"] == lv])
                     for lv in (5, 4, 3, 2, 1)]
            cls = ""
        else:
            specs = [("neg", "全部利空", neg_records)] + \
                    [(f"n{lv}", f"N{lv}", [r for r in neg_records if r["neg_level"] == lv])
                     for lv in (3, 2, 1)]
            cls = " neg"
        btns = []
        for gid, tag, rows in specs:
            if gid not in blk_groups:
                continue
            n = len(_main_codes(rows))
            btns.append(f'<button class="btn{cls}" onclick="addToBlock(\'{gid}\')" '
                        f'title="把「{tag}」这批股票加入通达信自定义板块（去重后 {n} 只）">'
                        f'{tag} {n}</button>')
        if not btns:
            return ""
        return ('<div class="btns"><span class="bl">加入通达信板块：</span>'
                + "".join(btns) + "</div>")

    p = ['<!DOCTYPE html>', '<html lang="zh-CN">', '<head>', '<meta charset="utf-8">',
         f"<title>个股利好 · 通达信版面 {date_str}</title>",
         "<style>" + TDX_STYLE + "</style>", "</head>", "<body>", '<div class="wrap">',
         '<header class="hd">',
         "<h1>个股利好 · 通达信版面</h1>",
         f'<span class="meta">数据日期 <b>{date_str}</b>　利好 <b>{len(records)}</b> 条'
         f'（L5 {pos_stats["level"].get(5, 0)} / L4 {pos_stats["level"].get(4, 0)}）　'
         f'利空 <b>{len(neg_records)}</b> 条（N3 {neg_stats["level"].get(3, 0)}）　'
         f'当日行情 {len(quoted)} 条　生成 {gen_time}　v{VERSION}</span>',
         '<div class="side">',
         '<span class="hint">点股票代码跳转通达信对应个股（在本页所在通达信内生效）</span>',
         "</div>",
         "</header>"]

    if not records:
        p.append('<div class="list"><p class="empty">本次未提取到符合条件的个股利好。</p></div>')
    else:
        p.append(_blk_bar("pos"))
        p.append('<div class="list">')
        p.append('<div class="row head-row"><span class="lv">档</span><span class="pc">当日</span>'
                 '<span class="code">代码 名称</span>'
                 '<span class="tier">层级</span><span class="cat">类别</span>'
                 '<span class="txt">利好摘要</span></div>')
        for r in sorted(records, key=_key):
            badge = (f'<span class="lv" style="background:{LEVEL_COLORS[r["level"]]}" '
                     f'title="{esc(LEVEL_NAME[r["level"]])}">{r["level"]}</span>')
            p.append(_row(r, badge, r["tier"], r["cat"]))
        p.append("</div>")

    # 利空警示：档位用冷色，附当日行情（跌幅越大越靠前）
    if neg_records:
        p.append(f'<div class="sect">利空警示'
                 f'<span>　{len(neg_records)} 条（N3 重大 {neg_stats["level"].get(3, 0)} / '
                 f'N2 实质 {neg_stats["level"].get(2, 0)} / N1 软 {neg_stats["level"].get(1, 0)}）'
                 f'　·　档位冷色，当日跌幅越大越靠前</span></div>')
        p.append(_blk_bar("neg"))
        p.append('<div class="list neg">')
        p.append('<div class="row head-row"><span class="lv">档</span><span class="pc">当日</span>'
                 '<span class="code">代码 名称</span>'
                 '<span class="tier">档位</span><span class="cat">类别</span>'
                 '<span class="txt">利空摘要</span></div>')
        for r in sorted(neg_records, key=lambda x: (-x["neg_level"],
                                                    x["pct_t0"] if x.get("pct_t0") is not None else 999)):
            badge = (f'<span class="lv" style="background:{NEG_LEVEL_COLORS[r["neg_level"]]}" '
                     f'title="{esc(NEG_LEVEL_NAME[r["neg_level"]])}">N{r["neg_level"]}</span>')
            p.append(_row(r, badge, NEG_LEVEL_NAME[r["neg_level"]], r["neg_cat"]))
        p.append("</div>")

    src = "、".join(ok_sources) if ok_sources else "无"
    if fail_sources:
        src += f"（失败：{'、'.join(fail_sources)}）"
    p += ['<footer>数据来源：' + esc(src) + f'　·　{mode}提取　·　本页每次提取整体覆盖，'
          '仅供信息参考，不构成投资建议。</footer>',
          "</div>"]
    if blk_groups:   # 通达信内部协议：内嵌浏览器拦截后把这批股票加入自定义板块
        p += ["<script>",
              "var BLK=" + json.dumps(blk_groups, ensure_ascii=False) + ";",
              "function addToBlock(k){var s=BLK[k];if(s){"
              "window.location.href='http://www.treeid/AddToBlock_'+s;}}",
              "</script>"]
    p += ["</body>", "</html>"]
    return "\n".join(p)


def next_run_after(now, hour=0, minute=15):
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now >= target:
        target += datetime.timedelta(days=1)
    return target


def auto_loop():
    print(f"[自动模式] 已启动，每天 {datetime.time(0, 15)} 自动提取前一日数据。Ctrl+C 退出。")
    while True:
        now = datetime.datetime.now()
        target = next_run_after(now)
        wait_sec = (target - now).total_seconds()
        print(f"[自动模式] 下次运行：{target:%Y-%m-%d %H:%M:%S}（{int(wait_sec)} 秒后）")
        time.sleep(wait_sec if wait_sec > 0 else 60)
        # 到点执行：报告日期 = 执行日-1（前一日完整数据）
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        ok = False
        try:
            run_extract(yesterday, mode="自动")
            ok = True
        except Exception as e:
            hist = {"ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "mode": "自动", "report_date": yesterday.strftime("%Y-%m-%d"),
                    "status": "error", "error": f"{type(e).__name__}: {e}"}
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(hist, ensure_ascii=False) + "\n")
            print(f"[自动模式] 执行失败：{e}")
        # 节假日/周末多日空档 → 自动把整个空档合成一份聚合报告
        if ok:
            try:
                prev = prev_report_date(yesterday)
                if prev is not None and (yesterday.date() - prev).days >= 2:
                    run_aggregate(prev + datetime.timedelta(days=1), yesterday, mode="自动聚合")
            except Exception as e:
                print(f"[自动模式] 多日聚合报告失败：{e}")


def task_target():
    """计划任务要执行的命令行：打包后直接调用 exe 自身，否则调用 python + 脚本。"""
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}" --run'
    return f'"{sys.executable}" "{os.path.abspath(__file__)}" --run'


def install_task():
    """注册 Windows 计划任务，返回结果文本（供命令行/GUI 共用）。"""
    cmd = ["schtasks", "/Create", "/TN", TASK_NAME, "/TR", task_target(),
           "/SC", "DAILY", "/ST", "00:15", "/F"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="gbk", errors="ignore")
        out = (r.stdout or r.stderr or "（无输出）").strip()
        if r.returncode == 0:
            return (f"{out}\n[OK] 已注册 Windows 计划任务「{TASK_NAME}」，每天 00:15 自动执行一次。\n"
                    f"     执行命令：{task_target()}")
        return f"{out}\n[提示] 注册失败，请以管理员身份运行本程序后重试。"
    except Exception as e:
        return f"注册计划任务失败：{type(e).__name__}: {e}"


def remove_task():
    """删除 Windows 计划任务，返回结果文本。"""
    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="gbk", errors="ignore")
        out = (r.stdout or r.stderr or "（无输出）").strip()
        return out + ("\n[OK] 已删除计划任务「%s」。" % TASK_NAME if r.returncode == 0
                      else "\n[提示] 任务可能不存在。")
    except Exception as e:
        return f"删除计划任务失败：{type(e).__name__}: {e}"


def show_history():
    if not os.path.exists(HISTORY_FILE):
        print("暂无历史提取记录。")
        return
    print(f"{'时间':<20}{'模式':<6}{'数据日期':<12}{'消息':<8}{'利好':<6}状态")
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                h = json.loads(line)
                print(f"{h.get('ts',''):<20}{h.get('mode',''):<6}{h.get('report_date',''):<12}"
                      f"{h.get('news_count','-'):<8}{h.get('stock_count','-'):<6}{h.get('status','')}  {h.get('report_file','')}")
            except Exception:
                continue
    print(f"\n历史记录文件：{HISTORY_FILE}")


def main():
    ap = argparse.ArgumentParser(description="个股利好提取器")
    ap.add_argument("--run", action="store_true", help="手动立即提取一次")
    ap.add_argument("--date", type=str, default=None, help="指定数据日期 YYYYMMDD（不填则为近24小时滚动窗口）")
    ap.add_argument("--window-hours", type=int, default=24, help="滚动窗口小时数（仅默认模式生效，默认 24；传 48 即最近 48 小时）")
    ap.add_argument("--auto", action="store_true", help="常驻模式，每天00:15自动提取前一日")
    ap.add_argument("--install-task", action="store_true", help="注册Windows计划任务(每天00:15)")
    ap.add_argument("--remove-task", action="store_true", help="删除Windows计划任务")
    ap.add_argument("--history", action="store_true", help="查看历史提取记录")
    ap.add_argument("--update-stocks", action="store_true", help="强制刷新全量A股代码表")
    ap.add_argument("--backfill", type=int, default=None,
                    help=f"批量回补最近 N 天(1~{MAX_HISTORY_DAYS_CNINFO})并落盘缓存")
    ap.add_argument("--review", type=int, nargs="?", const=MAX_HISTORY_DAYS_CNINFO, default=None,
                    help=f"按已回补缓存生成规则回测报告（默认近 {MAX_HISTORY_DAYS_CNINFO} 天）")
    ap.add_argument("--verify-selftest", action="store_true", help="行情解析自测（注入坏样本）")
    ap.add_argument("--aggregate", nargs="+", default=None,
                    help="多日聚合报告：传 1~2 个 YYYYMMDD（起始 [结束]，缺结束为今天）。"
                         "节假日/周末一次运行即可把区间内多日数据汇总成一份报告")
    args = ap.parse_args()

    if args.auto:
        auto_loop()
        return
    if args.install_task:
        print(install_task())
        return
    if args.remove_task:
        print(remove_task())
        return
    if args.history:
        show_history()
        return
    if args.update_stocks:
        print("正在联网刷新全量A股代码表…")
        if update_stock_table():
            print(f"[OK] 代码表已更新：{STOCK_TABLE_CACHE}")
        else:
            print("[失败] 联网抓取不完整，代码表未更新。")
        return

    if args.verify_selftest:
        passed, fails = quote_selftest()
        print(f"[自测] 通过 {passed} 项，失败 {len(fails)} 项")
        for m in fails:
            print(f"       × {m}")
        return

    if args.review:
        run_review(args.review)
        return

    if args.backfill:
        run_backfill(args.backfill)
        return

    if args.aggregate:
        if len(args.aggregate) < 1:
            print("--aggregate 至少需传一个起始日期 YYYYMMDD，如 --aggregate 20261001 20261007")
            return
        try:
            sd = datetime.datetime.strptime(args.aggregate[0], "%Y%m%d")
        except ValueError:
            print("起始日期格式错误，应为 YYYYMMDD，如 20261001")
            return
        if len(args.aggregate) >= 2:
            try:
                ed = datetime.datetime.strptime(args.aggregate[1], "%Y%m%d")
            except ValueError:
                print("结束日期格式错误，应为 YYYYMMDD，如 20261007")
                return
        else:
            ed = datetime.datetime.now()
        run_aggregate(sd, ed, mode="手动聚合")
        return

    if args.date:
        try:
            d = datetime.datetime.strptime(args.date, "%Y%m%d")
        except ValueError:
            print("日期格式错误，应为 YYYYMMDD，如 20260918")
            return
        run_extract(d, mode="手动")
    else:
        # 未指定日期时用近24小时滚动窗口：凌晨运行时也能出有效报告，而不是交白卷
        run_extract(datetime.datetime.now(), mode="手动", rolling=True, window_hours=args.window_hours)

if __name__ == "__main__":
    main()
