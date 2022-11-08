import string

import nanoid


def gen_random_str(n: int = 20) -> str:
    return nanoid.generate(string.ascii_letters + string.digits, n)
