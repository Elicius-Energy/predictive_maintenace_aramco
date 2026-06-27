import paho.mqtt.client as mqtt
import time

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("#")
    print("Subscribed to all topics")

def on_message(client, userdata, msg):
    print(f"[{msg.topic}] {msg.payload.decode('utf-8', errors='replace')}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Connecting to node.kaatru.org...")
client.connect("node.kaatru.org", 1883, 60)
client.loop_start()

time.sleep(10)
client.loop_stop()
