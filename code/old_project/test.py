import os
import webbrowser
import threading
import time
def startService():
    os.system("python app.py")
def openWeb():
    webbrowser.open('http://127.0.0.1:5000/', 0, False)

threads=[]
t1 = threading.Thread(target=startService)
threads.append(t1)
t2 = threading.Thread(target=openWeb)
threads.append(t2)

if __name__ == '__main__':
    for t in threads:
        t.setDaemon(True)
        t.start()
        time.sleep(2)





