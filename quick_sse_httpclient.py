import http.client
import json

HOST = "127.0.0.1"
PORT = 5000


def start_session():
    conn = http.client.HTTPConnection(HOST, PORT)
    payload = json.dumps({}).encode("utf-8")
    conn.request("POST", "/api/start_session", body=payload, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    data = resp.read().decode("utf-8", errors="replace")
    try:
        obj = json.loads(data)
    except Exception:
        print("client: start_session parse fail:", data[:200])
        conn.close()
        return None
    conn.close()
    print("client: start_session resp:", obj)
    return obj.get("session_id")


def stream_chat(session_id):
    conn = http.client.HTTPConnection(HOST, PORT)
    payload = json.dumps({"session_id": session_id, "message": "测试一下流式输出，简要回答。"}).encode("utf-8")
    conn.request("POST", "/api/chat/stream", body=payload, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    print("client: stream status:", resp.status)
    if resp.status != 200:
        body = resp.read().decode("utf-8", errors="replace")
        print("client: stream failed body:", body[:200])
        conn.close()
        return
    print("client: reading stream...")
    while True:
        chunk = resp.read(1024)
        if not chunk:
            break
        print("client: chunk:", chunk.decode("utf-8", errors="replace")[:160])
    conn.close()
    print("client: stream closed")


if __name__ == "__main__":
    sid