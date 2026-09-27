import sqlite3
conn = sqlite3.connect('/app/bugforge.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables])
runs = conn.execute("SELECT id, status, scenario_id, started_at, finished_at FROM runs ORDER BY id DESC LIMIT 10").fetchall()
print('Runs:')
for r in runs:
    print(f'  id={r[0]} status={r[1]} scenario={r[2]} started={r[3]} finished={r[4]}')
steps = conn.execute("SELECT id, run_id, step_index, fault_type, target_service, status FROM run_steps ORDER BY id DESC LIMIT 20").fetchall()
print('Steps:')
for s in steps:
    print(f'  id={s[0]} run={s[1]} step={s[2]} fault={s[3]} target={s[4]} status={s[5]}')
conn.close()
