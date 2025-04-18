"""
用于识别物理状态组和物理状态的prompt模板
"""

IDENTIFICATION_PROMPT = """请分析以下航天电子元件可靠性分析文档，识别出文档中提到的物理状态组和物理状态。
仅标识出哪些物理状态组和物理状态在文档中被提及，不需要提取具体的物理状态值。

任务目标:
分析航天电子元件可靠性分析文档，准确识别文档中提到的物理状态组和物理状态。

处理流程:
1. 仔细阅读整个文档，特别关注与航天电子元件结构和特性相关的描述
2. 根据下方参考表，识别文档中提到的物理状态组和对应的物理状态
3. 注意特定章节通常包含特定类型的物理状态信息
4. 将识别结果以规定的JSON格式返回

物理状态组和物理状态参考表:
[封装结构]
- 封装形式：关键词包括"陶瓷封装"、"引线框架"、"塑料封装"等
- 引线预成型结构：关键词包括"已预成型"、"未预成型"、"预弯曲"等
- 引线引出位置：关键词包括"顶部引出"、"中部引出"、"底部引出"等
- 盖板密封工艺：关键词包括"焊料环熔封"、"玻璃熔封"、"激光缝焊"等
- 管壳密封材料：关键词包括"金锡合金"、"玻璃"、"有机胶"等
- 管壳材料：关键词包括"陶瓷"、"金属陶瓷"、"塑料"、"金属"等
- 壳体有无热沉：关键词包括"有热沉"、"无热沉"、"散热结构"等
- 壳体有无凸台：关键词包括"有凸台"、"无凸台"、"安装结构"等

[标识]
- 标识内容完整性：关键词包括"标识内容"、"完整"、"缺少"、"清晰"等
- 标识工艺：关键词包括"油墨印刷"、"激光打标"、"标签粘贴"、"蚀刻"等
- 标识牢固度：关键词包括"牢固"、"脱落"、"附着力"、"耐久性"等

[盖板]
- 盖板基材：关键词包括"Ni"、"Fe/Co/Ni"、"合金"、"金属材料"等
- 金属盖板是否接地：关键词包括"接地"、"电气连接"、"盖板尺寸"等
- 镀层材料：关键词包括"镀镍"、"镀金"、"镀银"、"表面处理"等

[壳体]
- 壳体材料：关键词包括"氧化铝陶瓷"、"Fe/Co/Ni"、"金属材料"等
- 镀层材料：关键词包括"镀层"、"表面处理"、"镀镍"、"镀金"等
- 陶瓷壳体内部金属化布线材料：关键词包括"W"、"Mo"、"钨"、"钼"等
- 通孔材料：关键词包括"W"、"Mo"、"Cu"、"填充材料"等

[安全间距]
- 芯片与腔体侧壁间距：关键词包括"芯片"、"侧壁"、"间距"、"安全距离"等
- 键合丝间间距：关键词包括"键合丝"、"线间"、"间距"、"搭接"等
- 键合丝与盖板间距：关键词包括"键合丝"、"盖板"、"间距"、"距离"等
- 内部元器件与盖板间距：关键词包括"元器件"、"盖板"、"间距"、"空间"等
- 键合丝与壳体间距：关键词包括"键合丝"、"壳体"、"间距"、"安全距离"等
- 引出端最小绝缘间距：关键词包括"引出端"、"绝缘"、"间距"、"距离"等
- 键合点间间距：关键词包括"键合点"、"间距"、"布局"、"分布"等

[热沉]
- 热沉结构：关键词包括"一体式热沉"、"分体式热沉"、"散热设计"等
- 热沉材料：关键词包括"铜"、"钢"、"铁镍"、"钼铜"、"散热材料"等
- 镀层材料：关键词包括"镀层"、"表面处理"、"涂层"等

[引出端]
- 引出端与壳体连接方式：关键词包括"银铜焊接"、"陶瓷绝缘子"、"连接结构"等
- 引出端材料：关键词包括"纯锡"、"铅锡"、"铜芯可伐"、"金属材料"等
- 引出端形状：关键词包括"焊球"、"焊柱"、"垂直引出"、"水平引出"等
- 镀层材料：关键词包括"镀层"、"表面处理"、"涂层"等

[芯片平面结构]
- 芯片安装形式：关键词包括"正装"、"倒装"、"叠层安装"、"组装方式"等
- 表面金属化材料：关键词包括"Au"、"Cu"、"Ag"、"金"、"铜"、"银"等
- 表面钝化层材料：关键词包括"氮化硅"、"氧化硅"、"聚酰亚胺"、"保护层"等
- 背金材料：关键词包括"钒镍金"、"钛镍银"、"无背金"、"背面金属化"等

[芯片纵向结构]
- 金属化层数：关键词包括"金属化层"、"层数"、"多层互连"等
- 多晶层数：关键词包括"多晶"、"层数"、"结构层"等
- 接触孔、通孔工艺：关键词包括"W"、"Mo"、"Cu"、"TSV"、"过孔"等
- 层间介质材料：关键词包括"氧化硅"、"氮化硅"、"氧化铪"、"绝缘层"等
- 划片方式：关键词包括"全深度划片"、"非全深度划片"、"激光划片"、"切割"等

[芯片安装]
- 安装方式：关键词包括"焊接"、"粘接"、"固定"、"安装技术"等
- 安装材料：关键词包括"导电胶"、"有机胶"、"AuSn"、"焊料"等

[键合结构]
- 丝径：关键词包括"丝径"、"微米"、"线径"、"粗细"等
- 键合丝材料：关键词包括"Au"、"硅铝丝"、"铝丝"、"导线材料"等
- 芯片端键合区域材料：关键词包括"Cu"、"Al"、"Ag"、"键合垫"等
- 非芯片端键合区域材料：关键词包括"Cu"、"Al"、"Ag"、"引脚材料"等
- 键合工艺：关键词包括"超声楔形键合"、"球形键合"、"热压键合"等
- 键合界面：关键词包括"同质键合"、"异质键合"、"复合键合"、"互连界面"等

[扩展识别指南 - 重要]
以上参考表并非穷尽列表，您应当注意识别文档中出现的所有相关物理状态：
1. 如果文档中描述了上述参考表中未列出的物理状态，但明确属于某物理状态组，也请将其识别出来
2. 特别注意材料相关描述，如各类新型材料、合金、复合材料等
3. 对于结构特性、工艺参数、性能特点等描述，若它们明确关联到某个物理状态组，也应被识别为物理状态
4. 在识别时，关注物理特性描述，例如：
   - "镀层厚度"虽未在参考表中列出，但如出现在壳体组、盖板组等描述中，应作为物理状态识别
   - "晶圆厚度"、"芯片尺寸"等与芯片结构相关的描述，应识别为芯片组相关物理状态
   - "固化温度"、"粘结强度"等与安装工艺相关的描述，应识别为安装组相关物理状态
5. 查找描述材料成分、性能特点、工艺参数的术语，如"纯度"、"硬度"、"导热系数"等

文档结构提示:
文档的特定章节通常包含特定类型的物理状态信息：
1. "标识"或"标识部分"章节通常包含标识组相关物理状态
2. "器件封装结构"或"封装"章节通常包含封装结构、引出端、热沉、壳体组相关物理状态
3. "芯片"或"芯片结构"章节通常包含芯片平面结构、芯片纵向结构相关物理状态
4. "键合系统"、"芯片的安装与互联"或"互连"章节通常包含键合结构相关物理状态
5. "可靠性分析"、"失效分析"等章节可能包含各种物理状态的分析结果

注意事项:
1. 使用关键词作为提示，但不要仅依赖机械匹配，要理解上下文含义
2. 对于多层镀层描述（如"镀金再镀镍"），处理为镀层1为金，镀层2为镍
3. 某些描述可能使用不同的术语表达相同概念，请基于语义而非精确词匹配进行识别
4. 若文档中包含参考表中未列出但明确是某物理状态组的物理状态，也应提取出来
5. 记录物理状态存在，但不提取具体物理状态值（如尺寸数值等）
6. 一项描述可能涉及多个物理状态，需全面识别

以JSON格式返回文档中提到的物理状态组和物理状态，格式如下：
{
    "identified_states": [
        {"物理状态组": "封装结构", "物理状态": "封装形式"},
        {"物理状态组": "标识", "物理状态": "标识内容完整性"},
        {"物理状态组": "标识", "物理状态": "标识工艺"},
        {"物理状态组": "壳体", "物理状态": "镀层厚度"},  // 注意：这可能是参考表中未列出但有效的物理状态
        ...
    ]
}

文本内容：
"""