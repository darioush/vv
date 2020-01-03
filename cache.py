import sqlite3
import os
import requests
import typing

from datetime import datetime, timedelta


headers = {
    'x-rapidapi-host': "skyscanner-skyscanner-flight-search-v1.p.rapidapi.com",
    'x-rapidapi-key': "5d955ce471msh6ea87e959706d38p1368edjsn2156a356b74a"
}

db = None
CACHE_TIME = timedelta(hours=12)
DEFAULT_PATH = os.path.join(os.path.dirname(__file__), 'cache.sqlite3')
epoch = datetime.utcfromtimestamp(0)


def unix_time(dt: datetime) -> int:
    return int((dt - epoch).total_seconds())


def get_db():
    global db
    if db is None:
        db = sqlite3.connect(DEFAULT_PATH)
        cur = db.cursor()
        sql = '''CREATE TABLE IF NOT EXISTS cache(
            key text NOT NULL PRIMARY KEY,
            received_timestamp integer NOT NULL,
            response text NOT NULL)'''
        cur.execute(sql)
    return db


def get_cached(key: str) -> typing.Optional[str]:
    cur = get_db().cursor()
    sql = 'SELECT received_timestamp, response FROM cache WHERE key=?'
    results = cur.execute(sql, (key,)).fetchone()
    if results is None:
        return None
    received, response = results
    if datetime.now() > datetime.fromtimestamp(received) + CACHE_TIME:
        return None
    return response


def cache(key: str, value: str) -> None:
    cur = get_db().cursor()
    now = unix_time(datetime.now())
    sql = 'UPDATE cache SET received_timestamp=?, response=? WHERE key=?'
    results = cur.execute(sql, (now, value, key))
    if results.rowcount > 0:
        get_db().commit()
        return
    sql = 'INSERT INTO cache (key, received_timestamp, response) VALUES (?, ?, ?)'
    results = cur.execute(sql, (key, now, value))
    get_db().commit()
    

def get_quotes(orig: str, dest: str, outbound: str, inbound: str = '') -> str:
    url = f'https://skyscanner-skyscanner-flight-search-v1.p.rapidapi.com/apiservices/browsequotes/v1.0/US/USD/en-US/{orig}/{dest}/{outbound}'
    if inbound:
        url += f'/{inbound}'
    
    key = '|'.join((orig, dest, outbound, inbound))
    cached = get_cached(key)
    if cached:
        return cached

    response = requests.request("GET", url, headers=headers)
    cache(key, response.text)
    return response.text
