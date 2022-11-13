"""
- Consultation(咨询项目类型)
    - Column:
        - avatar: "http://..../xx.png"
        - title: 环评
        - description: 规划环评，项目环评，后评价，跟踪评价
    - example：
        - 环评
        - 验收
        - 环保管家
        - 场地调查
        - 环保工程
        - 应急预案
        - 环境监理
        - 其他咨询
        - 萤火计划
- ConsultationProject(咨询项目内容)
    - Column:
        - title: relation to Consultation.title
        - content
"""