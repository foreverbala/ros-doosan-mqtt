from abc import ABCMeta
from typing import Optional, Type, Dict, Union

import inject
import paho.mqtt.client as mqtt
import rospy
import json
import sympy
from mqtt_bridge.msg import msgMqttSub
from dsr_msgs.msg import JogMultiAxis


from .util import lookup_object, extract_values, populate_instance


def create_bridge(factory: Union[str, "Bridge"], msg_type: Union[str, Type[rospy.Message]], topic_from: str,
                  topic_to: str, frequency: Optional[float] = None, **kwargs) -> "Bridge":
    """ generate bridge instance using factory callable and arguments. if `factory` or `meg_type` is provided as string,
     this function will convert it to a corresponding object.
    """
    if isinstance(factory, str):
        factory = lookup_object(factory)
    if not issubclass(factory, Bridge):
        raise ValueError("factory should be Bridge subclass")
    if isinstance(msg_type, str):
        msg_type = lookup_object(msg_type)
    if not issubclass(msg_type, rospy.Message):
        raise TypeError(
            "msg_type should be rospy.Message instance or its string"
            "reprensentation")
    return factory(
        topic_from=topic_from, topic_to=topic_to, msg_type=msg_type, frequency=frequency, **kwargs)


class Bridge(object, metaclass=ABCMeta):
    """ Bridge base class """
    _mqtt_client = inject.attr(mqtt.Client)
    _serialize = inject.attr('serializer')
    _deserialize = inject.attr('deserializer')
    _extract_private_path = inject.attr('mqtt_private_path_extractor')


class RosToMqttBridge(Bridge):
    """ Bridge from ROS topic to MQTT

    bridge ROS messages on `topic_from` to MQTT topic `topic_to`. expect `msg_type` ROS message type.
    """

    def __init__(self, topic_from: str, topic_to: str, msg_type: rospy.Message, frequency: Optional[float] = None):
        self._topic_from = topic_from
        self._topic_to = self._extract_private_path(topic_to)
        self._last_published = rospy.get_time()
        self._interval = 0 if frequency is None else 1.0 / frequency
        rospy.Subscriber(topic_from, msg_type, self._callback_ros)

    def _callback_ros(self, msg: rospy.Message):
        rospy.logdebug("ROS received from {}".format(self._topic_from))
        now = rospy.get_time()
        if now - self._last_published >= self._interval:
            self._publish(msg)
            self._last_published = now

    def _publish(self, msg: rospy.Message):
        payload = self._serialize(extract_values(msg))
        self._mqtt_client.publish(topic=self._topic_to, payload=payload)


class MqttToRosBridge(Bridge):
    """ Bridge from MQTT to ROS topic

    bridge MQTT messages on `topic_from` to ROS topic `topic_to`. MQTT messages will be converted to `msg_type`.
    """

    def __init__(self, topic_from: str, topic_to: str, msg_type: Type[rospy.Message],
                 frequency: Optional[float] = None, queue_size: int = 10):
        self._topic_from = self._extract_private_path(topic_from)
        self._topic_to = topic_to
        self._msg_type = msg_type
        self._queue_size = queue_size
        self._last_published = rospy.get_time()
        self._interval = None if frequency is None else 1.0 / frequency
        # Adding the correct topic to subscribe to
        self._mqtt_client.subscribe(self._topic_from)
        self._mqtt_client.message_callback_add(self._topic_from, self._callback_mqtt)
        self._publisher = rospy.Publisher(self._topic_to, self._msg_type, queue_size=self._queue_size)

        # rostopic in which the messages are published
        self.ros_pub1 = rospy.Publisher('/mqtt_sub', msgMqttSub, queue_size=10)
        # self.ros_pub2 = rospy.Publisher('/dsr01a0509/jog_multi', JogMultiAxis, queue_size=10)


    def _callback_mqtt(self, client: mqtt.Client, userdata: Dict, mqtt_msg: mqtt.MQTTMessage):
        """ callback from MQTT """
        str_payload = str(mqtt_msg.payload.decode("utf-8"))
        dict_payload = json.loads(str_payload)
        print("Received message: " , dict_payload )
        print("MQTT messages received from topic {}".format(mqtt_msg.topic))
        now = rospy.get_time()

        # sepearting the values from dictionary
        list_payload = list(dict_payload.values())
        # list_payload[3] = 0
        # list_payload[4] = 0
        # list_payload[5] = 0
        # list_payload[6] = 0

        value_4 = 0
        value_5 = -70
        value_6 = 0

        rx = 0
        ry = 90
        rz = 0
        # getting button values
        button_list = ( list_payload[3], list_payload[4], list_payload[5], list_payload[6])

        # sepearting the x,y,z values from the list
        # seperated_list = (list_payload[0],list_payload[1],list_payload[2],value_4,value_5,value_6)
        seperated_list = (list_payload[0],list_payload[1],list_payload[2],rx,ry,rz)

        joystick_maximum_value = 65535
        joystick_minimum_value1 = 0
        joystick_minimum_value2 = 32767
        joint1 = 360
        joint2 = 95
        joint3 = 135
        joint4 = 360
        joint5 = 135
        joint6 = 360

        x = 50
        y = 50
        z = 50
      

        # converted_payload0 = ((joint1*list_payload[0])/joystick_maximum_value)
        # converted_payload1 = ((joint2*list_payload[1])/joystick_maximum_value)
        # converted_payload2 = ((joint3*list_payload[2])/joystick_maximum_value)

        # converted_payload0 = ((((list_payload[0])/joystick_minimum_value2)*joint1)-joint1)
        # converted_payload1 = ((((list_payload[1])/joystick_minimum_value2)*joint2)-joint2)
        # converted_payload2 = ((((list_payload[2])/joystick_minimum_value2)*joint3)-joint3)
        # Total_list = (converted_payload0,converted_payload1,converted_payload2,value_4,value_5,value_6)


        converted_payload0 = ((((list_payload[0])/joystick_minimum_value2)*x)-x)
        converted_payload1 = ((((list_payload[1])/joystick_minimum_value2)*y)-y)
        converted_payload2 = ((((list_payload[2])/joystick_minimum_value2)*z)-z)
        Total_list = (converted_payload0,converted_payload1,converted_payload2,rx,ry,rz)



        # Getting msgs in the msgMqttSub file
        msg_mqtt_sub = msgMqttSub()  
        msg_mqtt_sub.timestamp = rospy.Time.now()
        msg_mqtt_sub.topic = mqtt_msg.topic
        msg_mqtt_sub.message = Total_list
        msg_mqtt_sub.button = button_list
        # msg = JogMultiAxis()
        # msg.jog_axis = seperated_list
        # publishing the msg 
        self.ros_pub1.publish(msg_mqtt_sub)
        # self.ros_pub2.publish(msg)

        if self._interval is None or now - self._last_published >= self._interval:
            try:
                ros_msg = self._create_ros_message(mqtt_msg)
                self._publisher.publish(ros_msg)
                self._last_published = now
            except Exception as e:
                rospy.logerr(e)
                
    
    def _create_ros_message(self, mqtt_msg: mqtt.MQTTMessage) -> rospy.Message:
        """ create ROS message from MQTT payload """
        # Hack to enable both, messagepack and json deserialization.
        if self._serialize.__name__ == "packb":
            msg_dict = self._deserialize(mqtt_msg.payload, raw=False)
        else:
            msg_dict = self._deserialize(mqtt_msg.payload)
        return populate_instance(msg_dict, self._msg_type())
        


__all__ = ['create_bridge', 'Bridge', 'RosToMqttBridge', 'MqttToRosBridge','seperated_list']