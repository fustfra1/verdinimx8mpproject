#!/usr/bin/env python3
# Phytec 2022, V1.0

import sys
import os
import json
import time
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
from argparse import ArgumentParser
from pprint import pprint

import isp_json


def read_aec_enable(isp):
    request = {
        'id': 'ae.g.en',
        'streamid': 0,
    }

    data = isp.read_json(request)

    return data['enable']


def write_aec_enable(isp, enable=True):
    request = {
        'enable': enable,
        'id': 'ae.s.en',
        'streamid': 0,
    }

    isp.write_json(request)


def read_awb_enable(isp):
    request = {
        'id': 'awb.g.en',
        'streamid': 0,
    }

    data = isp.read_json(request)

    return data['enable']


def write_awb_enable(isp, enable=True):
    request = {
        'enable': enable,
        'id': 'awb.s.en',
        'streamid': 0,
    }

    isp.write_json(request)


def get_wb(isp):
    request = {
        'id': 'wb.g.cfg',
        'streamid': 0,
    }

    return isp.read_json(request)


def set_wb(isp, red=1.0, green=1.0, blue=1.0):
    request = {
        'matrix': [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        'offset': {
            'blue': 0,
            'green': 0,
            'red': 0,
        },
        'wb.gains': {
            'blue': blue,
            'green.b': green,
            'green.r': green,
            'red': red,
        },
        'id': 'wb.s.cfg',
        'streamid': 0,
    }

    isp.write_json(request)


def read_dwe_bypass(isp):
    request = {
        'id': 'dwe.g.params',
        'streamid': 0,
    }

    data = isp.read_json(request)

    return data['dwe']['bypass']


def write_dwe_bypass(isp, enable=True):
    request = {
        'id': 'dwe.s.bypass',
        'streamid': 0,
        'dwe': {
            'bypass': enable,
        }
    }

    isp.write_json(request)


def sensor_query(isp):
    request = {
        'id': 'sensor.query',
        'streamid': 0,
    }

    data = isp.read_json(request)

    return data


def handle_awb(isp, state='on', red=1.0, green=1.0, blue=1.0):
    if state == 'on':
        write_awb_enable(isp, True)
    elif state == 'off':
        write_awb_enable(isp, False)
    elif state == 'manual':
        write_awb_enable(isp, False)
        set_wb(isp, red=red, green=green, blue=blue)
    else:
        pprint(json.dumps(get_wb(isp), indent=4))


def handle_aec(isp, state='on'):
    if state == 'on':
        write_aec_enable(isp, True)
    else:
        write_aec_enable(isp, False)


def handle_dwe(isp, state='on'):
    if state == 'on':
        write_dwe_bypass(isp, False)
    else:
        write_dwe_bypass(isp, True)


def toggle_features(isp, waittime=5.0, red=1.0, green=1.0, blue=1.0):

    Gst.init(sys.argv)

    pipeline = Gst.Pipeline()

    # Create GStreamer elements with error checking
    src = Gst.ElementFactory.make('v4l2src', 'source')
    if not src:
        print("Error: Could not create 'v4l2src' element.")
        sys.exit(1)
    src.set_property('device', '/dev/video2')

    caps = Gst.Caps.from_string('video/x-raw,format=YUY2,width=4032,height=3040')

    videoconvert = Gst.ElementFactory.make('videoconvert', 'convert')
    if not videoconvert:
        print("Error: Could not create 'videoconvert' element.")
        sys.exit(1)

    # Create the waylandsink element
    waylandsink = Gst.ElementFactory.make('waylandsink', 'waylandsink')
    if not waylandsink:
        print("Error: Could not create 'waylandsink' element.")
        sys.exit(1)

    # Create fpsdisplaysink element
    fpsdisplaysink = Gst.ElementFactory.make('fpsdisplaysink', 'sink')
    if not fpsdisplaysink:
        print("Error: Could not create 'fpsdisplaysink' element.")
        sys.exit(1)

    # Set properties for fpsdisplaysink
    fpsdisplaysink.set_property('video-sink', waylandsink)  # Set to Gst.Element
    fpsdisplaysink.set_property('text-overlay', False)
    fpsdisplaysink.set_property('sync', False)

    # Add all elements to the pipeline
    elements = [src, videoconvert, fpsdisplaysink, waylandsink]
    for element in elements:
        pipeline.add(element)

    # Link elements together: v4l2src -> capsfilter -> videoconvert -> fpsdisplaysink -> waylandsink
    if not src.link_filtered(videoconvert, caps):
        print("Error: Could not link 'v4l2src' to 'videoconvert' with caps filter.")
        sys.exit(1)
    if not videoconvert.link(fpsdisplaysink):
        print("Error: Could not link 'videoconvert' to 'fpsdisplaysink'.")
        sys.exit(1)
    # Note: fpsdisplaysink manages the sink internally, so no need to link it to waylandsink
    # However, since we're explicitly setting 'video-sink', adding waylandsink to the pipeline ensures it's part of the lifecycle

    # Start playing the pipeline
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("Error: Unable to set the pipeline to the PLAYING state.")
        sys.exit(1)

    # Initialize ISP features
    write_dwe_bypass(isp, False)
    write_aec_enable(isp, True)
    write_awb_enable(isp, True)

    # Since we're removing textoverlay, we'll log the status instead of displaying it on the video
    print('Dewarp: ON  AWB: ON  AEC: ON')

    while True:
        try:
            time.sleep(waittime)
            print('Dewarp: OFF  AWB: ON  AEC: ON')
            write_dwe_bypass(isp, True)
            time.sleep(waittime)
            print('Dewarp: OFF  AWB: OFF  AEC: ON')
            write_awb_enable(isp, False)
            set_wb(isp, red=red, green=green, blue=blue)
            time.sleep(waittime)
            print('Dewarp: OFF  AWB: OFF  AEC: OFF')
            write_aec_enable(isp, False)
            time.sleep(waittime)

            write_aec_enable(isp, True)
            time.sleep(0.5)
            print('Dewarp: OFF  AWB: OFF  AEC: ON')
            time.sleep(waittime)
            write_awb_enable(isp, True)
            print('Dewarp: OFF  AWB: ON  AEC: ON')
            time.sleep(waittime)
            write_dwe_bypass(isp, False)
            print('Dewarp: ON  AWB: ON  AEC: ON')

        except KeyboardInterrupt:
            break

    pipeline.set_state(Gst.State.NULL)


def main(args):
    parser = ArgumentParser(description='PHYTEC i.MX 8MP ISP feature Demo')
    parser.add_argument('-t', '--time', type=float, default=5.0,
                        help='Waiting time in seconds')
    parser.add_argument('-r', type=float, dest='red',
                        help='red gain (manual)', default=1.0)
    parser.add_argument('-b', type=float, dest='blue',
                        help='blue gain (manual)', default=1.0)
    parser.add_argument('-g', type=float, dest='green',
                        help='green gain (manual)', default=1.0)

    args = parser.parse_args()

    vd = os.open('/dev/video2', os.O_RDWR | os.O_NONBLOCK, 0)
    isp = isp_json.IspJson(vd)

    toggle_features(isp, waittime=args.time,
                    red=args.red,
                    green=args.green,
                    blue=args.blue)

    os.close(vd)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
