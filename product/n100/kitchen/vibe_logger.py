#!/usr/bin/env python3
# Kitchen Vibe Index logger - reads MT2 audio classification results via ADB
# Logs to Postgres tazaos DB, table: kitchen_vibe_log
import subprocess, json, datetime, time, psycopg2

CONN = psycopg2.connect(dbname='tazaos', user='taza')

# YAMNet classes that map to positive vibes (laughter, cheering, applause)
GOOD_VIBE_CLASSES = {
    'Laughter', 'Cheering', 'Applause', 'Crowd', 'Chatter',
    'Music', 'Singing', 'Giggling', 'Hubbub, speech noise, speech babble',
}

# YAMNet classes that map to bad vibes (yelling, crashing, distress sounds)
BAD_VIBE_CLASSES = {
    'Screaming', 'Shout', 'Crying, sobbing', 'Yell',
    'Crash', 'Bang', 'Breaking', 'Shattering',
    'Whimper, dog', 'Groan', 'Sobbing',
}


def ensure_table():
    with CONN.cursor() as c:
        c.execute('''
            CREATE TABLE IF NOT EXISTS kitchen_vibe_log (
                id SERIAL PRIMARY KEY,
                ts TIMESTAMPTZ DEFAULT NOW(),
                device TEXT,
                vibe TEXT,
                confidence FLOAT,
                raw_label TEXT
            )
        ''')
    CONN.commit()


def classify_vibe(raw_label):
    if raw_label in GOOD_VIBE_CLASSES:
        return 'good'
    if raw_label in BAD_VIBE_CLASSES:
        return 'bad'
    return 'neutral'


def log_vibe(device, vibe, confidence, raw_label):
    with CONN.cursor() as c:
        c.execute(
            'INSERT INTO kitchen_vibe_log (device, vibe, confidence, raw_label) VALUES (%s,%s,%s,%s)',
            (device, vibe, confidence, raw_label)
        )
    CONN.commit()
    print(f'{datetime.datetime.now().isoformat()} [{device}] {vibe} ({confidence:.2f}) raw={raw_label}')


if __name__ == '__main__':
    ensure_table()
    print('Kitchen Vibe Index logger started')
    # Placeholder loop - real implementation reads ADB logcat for YAMNet output
    while True:
        time.sleep(30)
        print('vibe_logger heartbeat - awaiting model integration')
