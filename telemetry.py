import requests
import json
from hashlib import sha256
import time

BASE_URL='https://legallist-pgdb-prod.herokuapp.com/app/'

def authenticate_user(username):
    hashed_username = (sha256(str.encode(username))).hexdigest()
    auth_response = requests.get(
        BASE_URL + 'check/' + hashed_username)
    auth_status = json.loads(auth_response.content)
    print(f'Authentication: {auth_status}')
    return auth_status


def log_anon_usage(username, login_prefix, num_cases):
    url = BASE_URL + 'log'
    if login_prefix == "smustu":
        year = username.split('.')[-1]

    elif login_prefix == "smustf":
        year = ""

    payload = {
        "username_hash": sha256(str.encode(username)).hexdigest(),
        "usertype": login_prefix,
        "year": year,
        "timestamp": int(time.time()),
        "downloads": num_cases
    }

    r = requests.post(url, data=json.dumps(payload))
    print('Data logged')
