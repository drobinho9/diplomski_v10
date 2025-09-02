import sqlite3
conn = sqlite3.connect('instance/database.db')
c = conn.cursor()
c.execute("ALTER TABLE user ADD COLUMN medical_history TEXT;")
c.execute("ALTER TABLE user ADD COLUMN citizenship VARCHAR(100);")
conn.commit()
conn.close()