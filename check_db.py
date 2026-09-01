import sqlite3

# 连接数据库
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# 获取所有表名
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [row[0] for row in cursor.fetchall()]

# 显示每个表的结构
for table_name in tables:
    print(f"\n{table_name}表结构:")
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for column in columns:
        print(f"ID: {column[0]}, 名称: {column[1]}, 类型: {column[2]}, 是否为空: {column[3]}, 默认值: {column[4]}, 主键: {column[5]}")

# 关闭连接
cursor.close()
conn.close()