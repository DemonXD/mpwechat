"""
数据库初始化操作
"""

def command():
    from db import DB
    create_message_sql = """
    CREATE TABLE IF NOT EXISTS message(
        uid TEXT PRIMARY KEY,
        nickname VARCHAR(64),
        phone VARCHAR(16),
        email VARCHAR(64),
        address VARCHAR(512),
        content TEXT,
        created_at BIGINT NOT NULL
    );
    """
    create_announcement_sql = """
    CREATE TABLE IF NOT EXISTS announcement(
        uid TEXT PRIMARY KEY,
        title VARCHAR(256) NOT NULL,
        description VARCHAR(1024) NOT NULL,
        content TEXT NOT NULL,
        author VARCHAR(64) NOT NULL,
        published_time BIGINT NOT NULL
    );
    """
    create_consultation_sql = """
    CREATE TABLE IF NOT EXISTS consultation(
        uid TEXT PRIMARY KEY,
        avatar VARCHAR(512) NOT NULL,
        title VARCHAR(128) NOT NULL,
        description VARCHAR(512) NOT NULL
    );
    """
    create_consultation_content_sql = """
    CREATE TABLE IF NOT EXISTS consultation_content(
        uid TEXT PRIMARY KEY,
        content TEXT NOT NULL
    );
    """
    create_profile_sql = """
    CREATE TABLE IF NOT EXISTS profile(
        uid TEXT PRIMARY KEY,
        section_name VARCHAR(64) NOT NULL,
        content TEXT NOT NULL
    )
    """
    create_user_sql = """
    CREATE TABLE IF NOT EXISTS user(
        uid TEXT PRIMARY KEY,
        username VARCHAR(32) NOT NULL,
        password VARCHAR(128) NOT NULL
    )
    """
    with DB():
        try:
            DB.session.execute(create_announcement_sql)
            DB.session.execute(create_consultation_sql)
            DB.session.execute(create_consultation_content_sql)
            DB.session.execute(create_message_sql)
            DB.session.execute(create_profile_sql)
            DB.session.execute(create_user_sql)
            DB.session.commit()
        except Exception as e:
            print("====", e)
            DB.session.rollback()
        else:
            # from homepage.models.announcement import Announcement
            # from homepage.models.consultation import Consultation, ConsultationContent
            # from homepage.models.message import Message
            # from homepage.models.profile import CompanyProfile
            from homepage.models.user import User
            if User.one_or_none(username="admin") is None:
                User.create(
                    username="admin",
                    password="admin"
                )
                print("init table successful and initial user: admin succeed")
            else:
                print("user:admin already exists")

