import sqlite3

def init_database():
    conn = sqlite3.connect('cyber_fortress.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            lockout_until REAL DEFAULT 0
        )
    ''')
    
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', 'Admin@1234'))
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('student', 'Student@123'))
        conn.commit()
        print("[+] Tạo cơ sở dữ liệu SQLite thành công!")
    except sqlite3.IntegrityError:
        print("[!] Cơ sở dữ liệu đã tồn tại.")
        
    conn.close()

if __name__ == '__main__':
    init_database()