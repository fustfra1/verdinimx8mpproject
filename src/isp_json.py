#!/usr/bin/env python3
# Phytec 2022, V1.0

import fcntl
import json
import ctypes

import v4l2_bindings as v4l2

V4L2_CID_VIV_EXTCTRL = int('0x98F901', 0)


class IspJson():
    def __init__(self, videodev):
        self.ec = v4l2.v4l2_ext_control()
        self.ecs = v4l2.v4l2_ext_controls()
        self.vd = videodev

        self._init()

    def _init(self):
        self.ec.id = V4L2_CID_VIV_EXTCTRL
        self.ec.size = 64 * 1024
        self.ecs.controls = ctypes.pointer(self.ec)
        self.ecs.count = 1
        self.ecs.ctrl_class = v4l2.V4L2_CTRL_CLASS_USER
        self.buffer = ctypes.create_string_buffer(b'\000' * self.ec.size)
        self.ec.string = ctypes.cast(self.buffer, ctypes.c_char_p)

        try:
            fcntl.ioctl(self.vd, v4l2.VIDIOC_G_EXT_CTRLS, self.ecs)
        except OSError:
            pass

    def _get_ctrls(self):
        ctypes.memset(self.buffer, 0, self.ec.size)
        fcntl.ioctl(self.vd, v4l2.VIDIOC_G_EXT_CTRLS, self.ecs)

        return json.loads(self.buffer.value)

    def _set_ctrls(self, data):
        s_data = json.dumps(data, indent="\t")
        if len(s_data) >= self.ec.size:
            raise BufferError('Data size exceeds buffer size')

        ctypes.memmove(self.buffer, s_data.encode('utf-8'), len(s_data))
        fcntl.ioctl(self.vd, v4l2.VIDIOC_S_EXT_CTRLS, self.ecs)

    def read_json(self, get_data):
        self._set_ctrls(get_data)
        return self._get_ctrls()

    def write_json(self, set_data):
        self._set_ctrls(set_data)
        return self._get_ctrls()
