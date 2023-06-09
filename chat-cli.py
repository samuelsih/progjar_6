import json
import os
import socket


addr = ("localhost", 8000)


class ChatClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = addr
        self.sock.connect(self.server_address)
        self.tokenid = ""

    def proses(self, cmdline: str):
        j = cmdline.split(" ")
        try:
            command = j[0].strip()

            match command:
                case "auth":
                    username = j[1].strip()
                    password = j[2].strip()
                    return self.login(username, password)

                case "send":
                    usernameto = j[1].strip()
                    message = ""
                    for w in j[2:]:
                        message = "{} {}".format(message, w)
                    return self.sendmessage(usernameto, message)

                case "inbox":
                    self.inbox()

                case "group":
                    groups_to = j[1].strip()
                    message = ""
                    for w in j[2:]:
                        message = "{} {}".format(message, w)

                    return self.group(groups_to, message)

                case "send-realm":
                    destination = j[1].strip()
                    message = ""
                    for w in j[2:]:
                        message = "{} {}".format(message, w)

                    return self.send_realm(destination, message)

                case "group-realm":
                    destination = j[1].strip()
                    message = ""
                    for w in j[2:]:
                        message = "{} {}".format(message, w)

                    return self.send_group_realm(destination, message)

                case "inbox-realm":
                    destination = j[1].strip()
                    return self.send_inbox_realm(destination)

        except IndexError:
            return "-Maaf, command tidak benar"

    def sendstring(self, string):
        try:
            self.sock.sendall(string.encode())
            receivemsg = ""
            while True:
                data = self.sock.recv(4096)
                print("diterima dari server", data)
                if data:
                    # data harus didecode agar dapat di operasikan dalam bentuk string
                    receivemsg = "{}{}".format(receivemsg, data.decode())
                    if receivemsg[-4:] == "\r\n\r\n":
                        print("end of string")
                        return json.loads(receivemsg)
        except:
            self.sock.close()
            return {"status": "ERROR", "message": "Gagal"}

    def login(self, username: str, password: str):
        string = "auth {} {} \r\n".format(username, password)
        result = self.sendstring(string)
        if result["status"] == "OK":
            self.tokenid = result["token"]
            return "username {} logged in, token {} ".format(username, self.tokenid)
        else:
            return "Error, {}".format(result["message"])

    def sendmessage(self, usernameto="xxx", message="xxx"):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "send {} {} {} \r\n".format(self.tokenid, usernameto, message)
        print(string)
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "message sent to {}".format(usernameto)
        else:
            return "Error, {}".format(result["message"])

    def inbox(self):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "inbox {} \r\n".format(self.tokenid)
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "{}".format(json.dumps(result["messages"]))
        else:
            return "Error, {}".format(result["message"])

    def group(self, to, message):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "group {} {} {} \r\n".format(self.tokenid, to, message)
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "{}".format(json.dumps(result["message"]))
        else:
            return "Error, {}".format(result["message"])

    def send_realm(self, destination: str, message: str):
        if self.tokenid == "":
            return "Error, not authorized"

        string = "send-realm {} {} {} \r\n".format(self.tokenid, destination, message)
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "{}".format(json.dumps(result["message"]))
        else:
            return "Error, {}".format(result["message"])

    def send_group_realm(self, destination: str, message: str):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "group-realm {} {} {} \r\n".format(self.tokenid, destination, message)
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "{}".format(json.dumps(result))
        else:
            return "Error, {}".format(result)

    def send_inbox_realm(self, destination: str):
        if self.tokenid == "":
            return "Error, not authorized"

        string = "inbox-realm {} \r\n".format(destination)
        result = self.sendstring(string)
        if result["status"] == "OK":
            return "{}".format(json.dumps(result["messages"]))
        else:
            return "Error, {}".format(result["messages"])


if __name__ == "__main__":
    cc = ChatClient()
    while True:
        cmdline = input("Command {}: ".format(cc.tokenid))
        print(cc.proses(cmdline))