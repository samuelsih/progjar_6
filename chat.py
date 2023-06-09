import threading
import socket
import json

from io import StringIO
from queue import Queue
from typing import Dict, Optional, Union
from copy import deepcopy

import shortuuid


class Realm(threading.Thread):
    def __init__(self, host: str, port: int, id: str, chat: "Chat"):
        self.id = id
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.addr = (host, port)
        self.chat = chat
        threading.Thread.__init__(self)

    def run(self):
        print(f"Running on realm: {self.id}")
        try:
            self.sock.connect(self.addr)
            while True:
                data = self.sock.recv(4096)
                if data:
                    cmd = data.decode()
                    result = self.chat.process_input(cmd)
                    json_result = json.dumps(result)

                    self.sock.sendall(json_result.encode())
        except Exception as e:
            print(e)
            self.sock.close()
            return {"status": "ERROR", "message": f"Gagal di realm: {self.id}"}


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
        self.realms: Dict[str, Realm] = {
            "realm1": Realm(
                host="localhost", port=8000, id="realm1", chat=deepcopy(self)
            ),
            "realm2": Realm(
                host="localhost", port=8000, id="realm2", chat=deepcopy(self)
            ),
        }

        for _, realm in self.realms.items():
            realm.start()

    def process_input(self, data: str) -> Dict:
        data = data.split(" ")
        print(data)
        try:
            cmd = data[0].strip()

            match cmd:
                case "auth":
                    # auth <USERNAME> <PASSWORD>
                    username = data[1].strip()
                    password = data[2].strip()

                    token = self.authenticate_user(username=username, password=password)
                    if token is None:
                        raise Exception("User tidak ada")

                    return {"status": "OK", "token": token}

                case "send":
                    # send <TOKEN> <TUJUAN> <PESAN>
                    token = data[1].strip()
                    username_to = data[2].strip()
                    msg = StringIO()

                    user_from = self.get_user_from_token(token)
                    if user_from is None:
                        raise Exception("User belum terauntetikasi")

                    if len(data[3:]) == 0:
                        raise IndexError

                    for m in data[3:]:
                        msg.write(f"{m} ")

                    return self.send_msg(
                        username_from=self.get_username_by_dict(user_from),
                        username_to=username_to,
                        msg=msg.getvalue(),
                    )

                case "group":
                    # group <TOKEN> <USER1>.<USER2>.<USER DSB> <PESAN>
                    token = data[1].strip()
                    username_lists = data[2].strip().split(".")
                    msg = StringIO()

                    user_from = self.get_user_from_token(token)
                    if user_from is None:
                        raise Exception("User belum terauntetikasi")

                    if len(username_lists) == 0:
                        raise IndexError

                    if len(data[3:]) == 0:
                        raise IndexError

                    for m in data[3:]:
                        msg.write(f"{m} ")

                    return self.send_group(
                        username_from=self.get_username_by_dict(user_from),
                        username_to_send_lists=username_lists,
                        msg=msg.getvalue(),
                    )

                case "inbox":
                    # inbox <TOKEN>
                    token = data[1].strip()
                    username = self.get_username_from_token(token)
                    if username is None:
                        raise Exception("User belum terauntetikasi")

                    return self.get_inbox(username)

                case "send-realm":
                    # send-realm <TOKEN> <TUJUAN>@<REALM_ID> <PESAN>
                    token = data[1].strip()
                    user_from = self.get_user_from_token(token)
                    if user_from is None:
                        raise Exception("User belum terauntetikasi")

                    username_to, realm_id = data[2].strip().split("@")
                    if realm_id not in self.realms:
                        raise Exception("Realm tidak ditemukan")

                    msg = StringIO()

                    if len(data[3:]) == 0:
                        raise IndexError

                    for m in data[3:]:
                        msg.write(f"{m} ")

                    return self.realms[realm_id].chat.send_msg(
                        msg=msg.getvalue(),
                        username_from=self.get_username_by_dict(user_from),
                        username_to=username_to,
                    )

                case "group-realm":
                    # group-realm <TOKEN> <TUJUAN_1>@<REALM_ID>.<TUJUAN_2>@<REALM_ID>.<TUJUAN_3>@<REALM_ID> <PESAN>
                    token = data[1].strip()
                    user_from = self.get_user_from_token(token)
                    if user_from is None:
                        raise Exception("User belum terauntetikasi")

                    username_lists = data[2].strip()
                    if len(username_lists) == 0:
                        raise IndexError

                    msg = StringIO()

                    if len(data[3:]) == 0:
                        raise IndexError

                    for m in data[3:]:
                        msg.write(f"{m} ")

                    print(username_lists, msg.getvalue())

                    return self.send_group_realm(
                        username_from=self.get_username_by_dict(user_from),
                        destination=username_lists,
                        msg=msg.getvalue(),
                    )

                case "inbox-realm":
                    # hanya untuk debug
                    username, realm_id = data[1].strip().split("@")
                    return self.realms[realm_id].chat.get_inbox(
                        username=username, realm_id=realm_id
                    )

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

    def send_msg(self, msg: str, username_from: str, username_to: str) -> Dict:
        user_from = self.get_user_by_username(username_from)
        if user_from is None:
            raise Exception("User belum terauntetikasi")

        user_to = self.get_user_by_username(username_to)
        if user_to is None:
            raise Exception("User yang diinginkan tidak ditemukan")

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

    def send_group(
        self, username_from: str, username_to_send_lists: list[str], msg: str
    ) -> Dict:
        
        for ug in username_to_send_lists:
            user = self.get_user_by_username(ug)
            if user is None:
                raise Exception("User yang diinginkan tidak ditemukan")

        for user_to in username_to_send_lists:
            self.send_msg(username_from=username_from, username_to=user_to, msg=msg)

        return {"status": "OK", "message": f"Message Sent to {', '.join(username_to_send_lists)}"}

    def get_inbox(self, username: str, realm_id: str = "default") -> Dict:
        user_from = self.get_user_by_username(username)
        incoming = user_from["incoming"]

        msgs = {}

        for users in incoming:
            msgs[users] = []
            while not incoming[users].empty():
                msgs[users].append(user_from["incoming"][users].get_nowait())

        return {"status": "OK", "realm": realm_id, "messages": msgs}

    def send_group_realm(self, username_from: str, destination: str, msg: str) -> Dict:
        user_from = self.get_user_by_username(username_from)
        if user_from is None:
            raise Exception("User tidak ada")

        reformat_destination = self.__rearrange_realm_destination(destination)

        response = {"status": "OK"}

        for realm_id, users in reformat_destination.items():
            result = self.realms[realm_id].chat.send_group(
                username_from=username_from, username_to_send_lists=users, msg=msg
            )
            response[realm_id] = result

        return response

    def __rearrange_realm_destination(self, destination: str) -> Dict:
        elements = destination.split(".")
        if len(elements) == 0:
            raise IndexError

        result: Dict[str, list[str]] = {}

        for element in elements:
            username, realm_id = element.split("@")

            if realm_id not in self.realms:
                raise Exception(f"Realm {realm_id} tidak ditemukan")

            if realm_id in result:
                result[realm_id].append(username)
            else:
                result[realm_id] = [username]
        
        return result


if __name__ == "__main__":
    j = Chat()
    while True:
        cmd = input("Command: ")
        print(j.process_input(cmd))