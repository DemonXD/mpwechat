"""
数据库设计
Model:
    - User
        - name
        - password
        - created
        - modified

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

    - CompanyProfile(公司简介)
        - Column:
            - sectionName
            - content


    - ProjectAnnouncement(项目公示)
        - Column:
            - title: 泰州市...项目竣工公示
            - description: content[:50]
            - content:
            - created
            - modified
            - author
    
    - message(留言)
        - nickname
        - phone
        - email
        - address
        - content
"""

def command():
    ...