#!/usr/bin/env python
import rospy
import sys
import paho.mqtt.client as mqtt
import json
from geometry_msgs.msg import PoseStamped, Quaternion, Point
from tf.transformations import quaternion_from_euler 
from std_msgs.msg import Int16, String
from visualization_msgs.msg import Marker
from ips.msg import Tag

class IPS:
    def __init__(self):
        self.ip_address = rospy.get_param('/ips_node/ip_address')
        self.port = rospy.get_param('/ips_node/port')

        self.node_dict_list = []
        self.p_list = []

        self.client = mqtt.Client()
    
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        self.client.on_message = self.on_message

        self.client.connect(self.ip_address, self.port)
        # self.client.subscribe('#', 1)
        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # to reconnect to mqtt broker even if the connection is broken.
            # run the subscriber in on_connect handler
            self.client.subscribe('#', 1)
            print("connected OK")
        else:
            print("Bad connection Returned code=", rc)


    def on_disconnect(self, client, userdata, flags, rc=0):
        print(str(rc))


    def on_subscribe(self, client, userdata, mid, granted_qos):
        print("subscribed: " + str(mid) + " " + str(granted_qos))


    def on_message(self, client, userdata, msg):
        # print(str(msg.topic.decode("utf-8")))
        # print(str(msg.payload.decode("utf-8")))
        self.message_processor(str(msg.topic.decode("utf-8")), msg.payload)

    def message_processor(self, topic, payload):
        if 'config' in topic:
            self.node_dict_list = self.config_msg_to_dict(self.node_dict_list, topic, payload)
        elif 'status' in topic:
            self.node_dict_list = self.status_msg_to_dict(self.node_dict_list, topic, payload)
        elif 'location' in topic:
            self.node_dict_list = self.location_msg_to_dict(self.node_dict_list, topic, payload)

        self.position_publisher(self.node_dict_list)
        self.text_marker_publisher(self.node_dict_list)
        self.sphere_marker_publisher(self.node_dict_list)
        
        # print(self.node_dict_list)
        # print('\n')

    def config_msg_to_dict(self, node_dict_list, topic, payload):

        node_dict = {}

        topic_list = topic.split('/')
        id = topic_list[2]

        pl_dict = json.loads(payload)
        label = str(pl_dict['configuration']['label'].decode("utf-8"))
        nodeType = str(pl_dict['configuration']['nodeType'].decode("utf-8"))

        for i in range(len(node_dict_list)):
            if node_dict_list[i]['id']==id:
                return node_dict_list

        if (nodeType=="ANCHOR"):
            # initiator = str(pl_dict['configuration']['anchor']['initiator'].decode("utf-8"))
            
            x = pl_dict['configuration']['anchor']['position']['x']
            y = pl_dict['configuration']['anchor']['position']['y']
            z = pl_dict['configuration']['anchor']['position']['z']
            quality = pl_dict['configuration']['anchor']['position']['quality']

            p_dict = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'quality': 0}
            p_dict['x'] = x
            p_dict['y'] = y
            p_dict['z'] = z
            p_dict['quality'] = quality

            node_dict = {'id': id, 'label': label, 'nodeType': nodeType, 'position': p_dict}
        else:
            node_dict = {'id': id, 'label': label, 'nodeType': nodeType}

        node_dict_list.append(node_dict)


        return node_dict_list
                
    def status_msg_to_dict(self, node_dict_list, topic, payload):
        
        topic_list = topic.split('/')
        id = topic_list[2]

        pl_dict = json.loads(payload)
        status = pl_dict['present']

        for i in range(len(node_dict_list)):
            if 'status' in node_dict_list[i]:
                return node_dict_list
            else:
                if node_dict_list[i]['id']==id:
                    node_dict_list[i]['status'] = status

        return node_dict_list

    def location_msg_to_dict(self, node_dict_list, topic, payload):
        
        if bool(payload) == False:
            return node_dict_list

        topic_list = topic.split('/')
        id = topic_list[2]

        pl_dict = json.loads(payload)
        x = pl_dict['position']['x']
        y = pl_dict['position']['y']
        z = pl_dict['position']['z']
        quality = pl_dict['position']['quality']



        for i in range(len(node_dict_list)):
            if node_dict_list[i]['id']==id:
                node_dict_list[i]['position'] = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'quality': 0}
                node_dict_list[i]['position']['x'] = x
                node_dict_list[i]['position']['y'] = y
                node_dict_list[i]['position']['z'] = z
                node_dict_list[i]['position']['quality'] = quality

                if (isinstance(node_dict_list[i]['position']['x'], float) == False) \
                    or (isinstance(node_dict_list[i]['position']['y'], float) == False) \
                    or (isinstance(node_dict_list[i]['position']['z'], float) == False):
                    
                    node_dict_list[i].pop('position', None)


        return node_dict_list

    def position_publisher(self, node_dict_list):
        
        p = Tag()

        for i in range(len(node_dict_list)):
            if 'position' in node_dict_list[i]:
                p.header.frame_id = 'map'
                p.header.stamp = rospy.Time.now()

                p.id.data = node_dict_list[i]['id']  
                p.position.x = node_dict_list[i]['position']['x']  
                p.position.y = node_dict_list[i]['position']['y']
                p.position.z = node_dict_list[i]['position']['z']
                p.quality.data = node_dict_list[i]['position']['quality']

                str_name = "/dwm/node/" + node_dict_list[i]['id'] + "/position"
                p_pub = rospy.Publisher(str_name, Tag, queue_size=10)

                p_pub.publish(p)

    def quality_publisher(self, node_dict_list):
        
        q = Int16()

        for i in range(len(node_dict_list)):
            if 'position' in node_dict_list[i]:

                q.data = node_dict_list[i]['position']['quality']  

                str_name = "/dwm/node/" + node_dict_list[i]['id'] + "/quality"
                q_pub = rospy.Publisher(str_name, Int16, queue_size=10)

                q_pub.publish(q)

    def text_marker_publisher(self, node_dict_list):
        
        marker = Marker()

        marker.header.frame_id = "/map"

        # set shape, Arrow: 0; Cube: 1 ; Sphere: 2 ; Cylinder: 3
        marker.type = 9
        marker.id = 0

        # Set the scale of the marker
        marker.scale.x = 0.5
        marker.scale.y = 0.5
        marker.scale.z = 0.5

        # Set the color
        marker.color.r = 1.0
        marker.color.g = 1.0
        marker.color.b = 1.0
        marker.color.a = 0.5

        for i in range(len(node_dict_list)):
            if 'position' in node_dict_list[i]:
                marker.header.stamp = rospy.Time.now()

                x = node_dict_list[i]['position']['x']  
                y = node_dict_list[i]['position']['y']
                z = node_dict_list[i]['position']['z']
                q = node_dict_list[i]['position']['quality']  

                # Set the pose of the marker
                marker.pose.position.x = x + 2.0
                marker.pose.position.y = y + 2.0
                marker.pose.position.z = z
                marker.pose.orientation.x = 0.0
                marker.pose.orientation.y = 0.0
                marker.pose.orientation.z = 0.0
                marker.pose.orientation.w = 1.0

                str_x = ""
                str_y = ""
                str_z = ""
                if x >= 0.0:
                    str_x = '+' + format(x, '.3f')
                else:
                    str_x = format(x, '.3f')

                if y >= 0.0:
                    str_y = '+' + format(y, '.3f')
                else:
                    str_y = format(y, '.3f')

                if z >= 0.0:
                    str_z = '+' + format(z, '.3f')
                else:
                    str_z = format(z, '.3f')

                # set text
                if node_dict_list[i]['nodeType'] == 'TAG':
                    str_text = "uwb_tag:\n" \
                                + "position[m]:" + "\n" \
                                + "  x:" + str_x + "\n" \
                                + "  y:" + str_y + "\n" \
                                + "  z:" + str_z + "\n" \
                                "quality: " + str(q) + "%"
                elif node_dict_list[i]['nodeType'] == 'ANCHOR':
                    str_text = "uwb_anchor:\n" \
                                + "position[m]:" + "\n" \
                                + "  x:" + str_x + "\n" \
                                + "  y:" + str_y + "\n" \
                                + "  z:" + str_z + "\n" \
                                "quality: " + str(q) + "%"
                marker.text = str_text

                str_name = "/dwm/node/" + node_dict_list[i]['id'] + "/text_marker"
                m_pub = rospy.Publisher(str_name, Marker, queue_size=10)

                m_pub.publish(marker)

    def sphere_marker_publisher(self, node_dict_list):
        
        marker = Marker()

        marker.header.frame_id = "/map"

        # set shape, Arrow: 0; Cube: 1 ; Sphere: 2 ; Cylinder: 3
        marker.type = 2
        marker.id = 0

        # Set the scale of the marker
        marker.scale.x = 0.2
        marker.scale.y = 0.2
        marker.scale.z = 0.2

        

        for i in range(len(node_dict_list)):
            if 'position' in node_dict_list[i]:
                marker.header.stamp = rospy.Time.now()

                x = node_dict_list[i]['position']['x']  
                y = node_dict_list[i]['position']['y']
                z = node_dict_list[i]['position']['z']
                q = node_dict_list[i]['position']['quality']  

                # Set the color
                marker.color.r = q*0.01
                marker.color.g = q*0.01
                marker.color.b = q*0.01
                marker.color.a = 1.0

                # Set the pose of the marker
                marker.pose.position.x = x
                marker.pose.position.y = y
                marker.pose.position.z = z
                marker.pose.orientation.x = 0.0
                marker.pose.orientation.y = 0.0
                marker.pose.orientation.z = 0.0
                marker.pose.orientation.w = 1.0

                str_name = "/dwm/node/" + node_dict_list[i]['id'] + "/sphere_marker"
                m_pub = rospy.Publisher(str_name, Marker, queue_size=10)

                m_pub.publish(marker)        

def main(args):
  rospy.init_node('ips', anonymous=True)
  ips = IPS()
  
  try:
    rospy.spin()
  except KeyboardInterrupt:
    print("Shutting down")

if __name__ == '__main__':
    main(sys.argv)