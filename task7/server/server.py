import socket
import threading
import time
import group

HOST = "88.198.53.236"
PORT = 80
IS_RUNNING = True
GROUPS = []
KNOWN_CLIENTS = []

def main():
    print("initializing socket")
    SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("trying to bind")
    try:
        SOCK.bind((HOST, PORT))
        print("bound!")
    except socket.error as msg:
        print("Bind failed. Error Code : " + str(msg[0]) + " Message " + msg[1])
        SOCK.close()
        sys.exit()
    print("listening")
    SOCK.listen(10)
    while IS_RUNNING:
        conn, addr = SOCK.accept()
        print("Connected to " + addr[0] + ":" + str(addr[1]))
        client = {
                "ADDR" : addr,
                "CONN" : conn
                }
        KNOWN_CLIENTS.append(client)
        thread = threading.Thread(None, listen_for_messages, None, (client,))
        thread.start()

def listen_for_messages(client):
    conn = client["CONN"]
    addr = client["ADDR"]
    while IS_RUNNING:
        data = recv_to_end(conn)
        data_str = data.decode("utf-8")
        msg_arr = data_str.split("\r\n")
        if msg_arr[0] == "dslp/1.2":
            if msg_arr[1] == "request time":
                client_response_time(client)
            elif msg_arr[1] == "group join":
                client_group_join(msg_arr[2], client)
            elif msg_arr[1] == "group leave":
                client_group_leave(msg_arr[2], client)
            elif msg_arr[1] == "group notify":
                client_group_notify(msg_arr[2], msg_arr[3], client)
            elif msg_arr[1] == "peer notify":
                client_peer_notify(msg_arr[2], msg_arr[3], msg_arr[4], client)
            else:
                send_error("Not a valid message type.", client)

def recv_to_end(CONN):
    ended = False
    while not ended:
        data = CONN.recv(4096)
        data_str = data.decode("utf-8")
        protocol_lines = data_str.split("\r\n")
        for line in protocol_lines:
            if line == ("dslp/end"):
                print(protocol_lines[1])
                ended = True
                break
        return data

def client_response_time(client):
    conn = client["CONN"]
    addr = client["ADDR"]
    date_time = time.time()
    # yyyy-MM-dd'T'HH:mm:ssX
    date_str = time.strftime("%Y-%m-%dT%H:%M:%S%Z", time.gmtime(date_time))
    message = "dslp/1.2\r\n" + "response time\r\n" + date_str + "\r\n" + "dslp/end\r\n"
    conn.sendall(message.encode("utf-8"))

def client_group_join(group_name, client):
    conn = client["CONN"]
    addr = client["ADDR"]
    group_exists = False
    group_index = 0
    for group_i in GROUPS:
        if group_name == group_i.get_group_name():
            group_exists = True
            group_i.add_member(conn, addr)
    if not group_exists:
        new_group = group.group(group_name)
        new_group.add_member(conn, addr)
        GROUPS.append(new_group)

"""
if the group exists,
the client is known,
the client is member of the group,
notify all other clients of this group with the message attached
"""
def client_group_leave(group_name, client):
    conn = client["CONN"]
    addr = client["ADDR"]
    group_exists = False
    group_is_member = False
    group_index = 0
    for group_i in GROUPS:
        if group_name == group_i.get_group_name():
            group_exists = True
            for member in group_i.get_members():
                if (str(conn) + str(addr)) == member["ID"]:
                    group_is_member = True
                    group_i.remove_member(conn, addr)
    if not group_exists:
        message = "The specified group doesn't exist."
        send_error(message, client)
    if not group_is_member:
        message = "User is not member of the specified group. You can't leave a group that you're not a member of."
        send_error(message, client)

"""
if the client is member of the group, 
notify all other clients of this group with the message attached
"""
def client_group_notify(group_name, msg, client):
    conn = client["CONN"]
    addr = client["ADDR"]
    group_exists = False
    group_is_member = False
    group_index = 0
    for group_i in GROUPS:
        if group_name == group_i.get_group_name():
            group_exists = True
            for member in group_i.get_members():
                if (str(conn) + str(addr)) == member["ID"]:
                    group_is_member = True
                    group_i.notify(msg)
    if not group_exists:
        message = "The specified group doesn't exist"
        send_error(message, client)
    if not group_is_member:
        message = "User is not member of the specified group. You can't send a message to a group that you're not a member of."
        send_error(message, client)

def client_peer_notify(peer, msg, file_str, client):
    conn = client["CONN"]
    addr = client["ADDR"]
    for client_i in KNOWN_CLIENTS:
        if addr == client_i["ADDR"]:
            message = "dslp/1.2\r\n" + "peer notify\r\n" + peer + "\r\n" + msg + "\r\n" + file_str + "\r\n" + "dslp/end\r\n"
            client_i["CONN"].sendall(message.encode("utf-8"))

def send_error(error, client):
    conn = client["CONN"]
    addr = client["ADDR"]
    message = "dslp/1.2\r\n" + "error\r\n" + str(error) + "\r\n" + "dslp/end\r\n"
    conn.sendall(message.encode("utf-8"))

if __name__ == "__main__":
    main()