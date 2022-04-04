
import threading
import datetime
import random
import rpyc
import sys
import time

date_time = datetime.datetime.now()

processes = []
ports = []
q = {}
critical_section_time = [10, 10]
time_out = [5, 5]
is_cs_available = False

class Process(threading.Thread):
    def __init__(self, id, data, state, timestamp, time_out, server):
        # creating server with thread in background
   
        threading.Thread.__init__(self, target=server.start)
        self.id = id
        self.data = None
        self.state = state
        self.timestamp = timestamp
        self.time_out = time_out
        self.server = server
  
        
    def release_cs(self):
        global is_cs_available
        self.state = "DO-NOT-WANT"
        is_cs_available = False
        self.timestamp = int(time.time()*10000)
        del q[self.id]

    def grant_access(self):
        self.state = "HELD"
        global is_cs_available
        cs_time = random.randint(critical_section_time[0], critical_section_time[1])
        is_cs_available = True
        threading.Timer(cs_time, self.release_cs).start()

    def change_state(self):
        if self.state == "DO-NOT-WANT":
            self.state = "WANTED"
            self.timestamp = int(time.time()*10000)
            responses = get_responses(self.id)
            q[self.id] =  self.timestamp
            if 'NO' not in responses and is_cs_available == False:
                self.timestamp = int(time.time()*10000)
                self.state = "HELD"
                self.grant_access()
        
    def change_state_when_timeout(self):
        threading.Timer(self.time_out, self.change_state).start()

class Service(rpyc.Service):
    def exposed_get_status(self, id):
        if processes[id].state == "DO-NOT-WANT":
            return "OK"
        else:
            return "NO" 

def create_threads(N):
    initial_state = "DO-NOT-WANT"
    port = 1758
    for i in range(N):
        initial_time_stamp = int(time.time()*10000)
        t_out = random.randint(time_out[0], time_out[1])
        server = rpyc.utils.server.ThreadedServer(Service, port = port)
        p = Process(i,"DS", initial_state, initial_time_stamp, t_out, server)
        processes.append(p)
        processes[i].daemon = True
        processes[i].start()
        ports.append(port)
        port += 1
        processes[i].change_state_when_timeout()

def access_cs():
    id = 0 
    if is_cs_available == False:
        if list(q.items()) != []:
            id = sorted(q.items(), key=lambda x: x[1], reverse=False)[0][0]
            processes[id].grant_access()

def list_p():
    for t in range(len(processes)):
        print(f"P{processes[t].id}, {processes[t].state}, {processes[t].timestamp}, {processes[t].time_out}") 

def get_responses(client_id):
    id = 0
    answers = []
    for port in ports:
        if id != client_id:
            conn = rpyc.connect('localhost', port)
            answers.append(conn.root.exposed_get_status(id))
        id += 1
    return answers

def update_threads_time_outs(t):
    newTime = t
    global time_out
    time_out[1] = newTime
    for p in processes:
        p.time_out = random.randint(time_out[0], time_out[1])

def change_status():
    for p in processes:
        p.change_state()

def stop():
    for p in processes:
        p.join() 

def main(argument):
   
    N = int(argument[1])
    if N < 0:
        print("N must be positive")
    else:
        create_threads(N)
        while True:
            command = input().lower().split(" ")
            cmd = command[0]

            if cmd == "list":
                list_p()
            elif cmd == "time-cs":
                global critical_section_time
                t = int(command[1])
                critical_section_time[1] = t
                print("Updated CS time")
            elif cmd == "time-p":
                t = int(command[1])
                update_threads_time_outs(t)
                print("Updated time out time")
            elif cmd == "exit":
                stop()
                break
            change_status()
            access_cs()
            

if __name__ == "__main__":
    main(sys.argv)