import hashlib
import json


def hash_solution(solution: object) -> str:
    payload = json.dumps(solution, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
