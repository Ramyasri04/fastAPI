import urllib.request
import json
from urllib.error import HTTPError
import asyncio
import asyncpg

def req(method, url, data=None, token=None):
    req = urllib.request.Request(url, method=method)
    if token: req.add_header('Authorization', f'Bearer {token}')
    if data:
        req.add_header('Content-Type', 'application/json')
        data = json.dumps(data).encode()
    try:
        with urllib.request.urlopen(req, data=data) as res:
            return res.status, res.read().decode()
    except HTTPError as e:
        return e.code, e.read().decode()

async def promote():
    conn = await asyncpg.connect('postgresql://postgres:postgres@auth-db:5432/auth_db')
    await conn.execute("UPDATE users SET role = 'super_admin' WHERE email = 'test@example.com'")
    await conn.close()

asyncio.run(promote())

status, body = req('POST', 'http://localhost:8001/auth/login', {'email': 'test@example.com', 'password': 'Password123'})
token = json.loads(body).get('access_token')

print('PATCH /auth/users/invalid_id/role:', req('PATCH', 'http://localhost:8001/auth/users/invalid_id/role', {'role': 'admin'}, token))
