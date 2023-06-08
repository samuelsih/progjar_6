from io import StringIO
from queue import Queue
from typing import Dict, Optional, Union

import shortuuid


class Chat:
    def __init__(self):
        self.sessions: Dict[str, str] = {}
        self.users: Dict[str, Union[str, Queue]] = {
            "messi": {
                "nama": "Lionel Messi",
                "negara": "Argentina",
                "password": "surabaya",
                "incoming": {},
                "outgoing": {},
            },
            "henderson": {
                "nama": "Jordan Henderson",
                "negara": "Inggris",
                "password": "surabaya",
                "incoming": {},
                "outgoing": {},
            },
            "lineker": {
                "nama": "Gary Lineker",
                "negara": "Inggris",
                "password": "surabaya",
                "incoming": {},
                "outgoing": {},
            },
        }

    def process_input(self, data: str) -> Dict:
        data = data.split(" ")
        print(data)
        try:
            cmd = data[0].strip()

            match cmd:
                case "auth":
                    username = data[1].strip()
                    password = data[2].strip()

                    token = self.authenticate_user(username=username, password=password)
                    if token is None:
                        raise Exception("User tidak ada")

                    return {"status": "OK", "token": token}

                case "send":
                    token = data[1].strip()
                    username_to = data[2].strip()
                    msg = StringIO()

                    user_from = self.get_user_from_token(token)
                    if user_from is None:
                        raise Exception("User belum terauntetikasi")

                    user_to = self.get_user_by_username(username_to)
                    if user_to is None:
                        raise Exception("User yang diinginkan tidak ditemukan")

                    if len(data[3:]) == 0:
                        raise IndexError

                    for m in data[3:]:
                        msg.write(f"{m} ")

                    return self.send_msg(
                        user_from=user_from, user_to=user_to, msg=msg.getvalue()
                    )

                case "group":
                    token = data[1].strip()
                    username_lists = data[2].strip().split(".")
                    msg = StringIO()

                    user_from = self.get_user_from_token(token)
                    if user_from is None:
                        raise Exception("User belum terauntetikasi")

                    if len(username_lists) == 0:
                        raise IndexError

                    user_groups = []
                    for ug in username_lists:
                        user = self.get_user_by_username(ug)
                        if user is None:
                            raise Exception("User yang diinginkan tidak ditemukan")

                        user_groups.append(user)

                    if len(data[3:]) == 0:
                        raise IndexError

                    for m in data[3:]:
                        msg.write(f"{m} ")

                    print(user_from, user_groups, msg.getvalue())

                    return self.send_group(
                        user_from=user_from, user_groups=user_groups, msg=msg.getvalue()
                    )
                
                case "inbox":
                    token = data[1].strip()
                    username = self.get_username_from_token(token)
                    if username is None:
                        raise Exception("User belum terauntetikasi")

                    return self.get_inbox(username)

                case _:
                    raise IndexError

        except KeyError:
            return {"status": "ERROR", "message": "Informasi tidak ditemukan"}
        except IndexError:
            return {"status": "ERROR", "message": "**Protocol Tidak Benar"}
        except Exception as e:
            return {"status": "ERROR", "message": f"{e}"}

    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        user = self.users.get(username, None)
        if user is None:
            return None

        if user["password"] != password:
            return None

        token = shortuuid.uuid()
        self.sessions[token] = username

        return token

    def get_user_from_token(self, token: str) -> Optional[Dict]:
        username = self.sessions.get(token, None)
        return None if username is None else self.users[username]

    def get_username_from_token(self, token: str) -> Optional[str]:
        return self.sessions.get(token, None)

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        try:
            return self.users[username]
        except KeyError:
            return None

    def get_username_by_dict(self, user: Dict) -> str:
        for key, val in self.users.items():
            if val == user:
                return key

        raise Exception("Terjadi kesalahan. Coba lagi")

    def send_msg(self, user_from: Dict, user_to: Dict, msg: str) -> Dict:
        message = {
            "msg_from": user_from["nama"],
            "msg_to": user_to["nama"],
            "msg": msg,
        }

        outqueue_sender = user_from["outgoing"]
        inqueue_receiver = user_to["incoming"]

        username_from = self.get_username_by_dict(user_from)

        try:
            outqueue_sender[username_from].put(message)
        except KeyError:
            outqueue_sender[username_from] = Queue()
            outqueue_sender[username_from].put(message)
        try:
            inqueue_receiver[username_from].put(message)
        except KeyError:
            inqueue_receiver[username_from] = Queue()
            inqueue_receiver[username_from].put(message)
        return {"status": "OK", "message": "Message Sent"}

    def send_group(self, user_from: Dict, user_groups: list[Dict], msg: str) -> Dict:
        to = []
        for user_to in user_groups:
            to.append(user_to["nama"])
            self.send_msg(user_from=user_from, user_to=user_to, msg=msg)

        return {"status": "OK", "message": f"Message Sent to {', '.join(to)}"}

    def get_inbox(self, username: str) -> Dict:
        user_from = self.get_user_by_username(username)
        incoming = user_from["incoming"]

        msgs = {}

        for users in incoming:
            msgs[users] = []
            while not incoming[users].empty():
                msgs[users].append(user_from["incoming"][users].get_nowait())

        return {"status": "OK", "messages": msgs}


if __name__ == "__main__":
    j = Chat()
    while True:
        cmd = input("Command: ")
        print(j.process_input(cmd))
