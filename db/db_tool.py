import sqlite3


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建表以存储课程 ID 和其他信息
    cursor.execute('''
                CREATE TABLE IF NOT EXISTS learn_record (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    semester INTEGER NOT NULL,
                    processed INTEGER DEFAULT 0,
                    UNIQUE(subject, course_id)
                )
            ''')

    conn.commit()
    conn.close()


def save_learn_record_to_db( db_path, subject, learn_record, semester):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for course_id in learn_record:
        try:
            cursor.execute('INSERT INTO learn_record (subject,course_id,semester) VALUES (?,?,?)',
                           (subject, course_id, semester,))
        except sqlite3.IntegrityError:
            print(f"课程 ID {course_id} 已存在，跳过插入")

    conn.commit()
    conn.close()


def get_last_processed_course_id(db_path, subject, semester):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        'SELECT course_id FROM learn_record WHERE processed = 0 and subject = ? and semester = ? ORDER BY id  LIMIT 1',
        (subject, semester,))
    last_processed = cursor.fetchone()

    conn.close()
    return last_processed[0] if last_processed else None


def mark_course_as_processed( db_path, subject, course_id, semester):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('UPDATE learn_record SET processed = 1 WHERE course_id = ? and subject = ? and semester = ?',
                   (course_id, subject, semester,))
    conn.commit()
    conn.close()

def clear_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM learn_record')
    conn.commit()
    conn.close()

def clear_db_by_subject(db_path,subject):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM learn_record where subject = ?',(subject,))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    db_path = 'learn_record.db'
    # save_learn_record_to_db(db_path, 'subject', ['course_id1', 'course_id2'], 1)
    # course_id = get_last_processed_course_id(db_path, '中国近现代史纲要(专升本)', 2)
    # print(course_id)
    # mark_course_as_processed(db_path, 'subject', 'course_id1', 1)
    # clear_db_by_subject(db_path,"数据库原理(专升本)")
    clear_db(db_path)