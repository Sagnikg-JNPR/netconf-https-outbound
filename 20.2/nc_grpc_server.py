"""This is test gRPC server implemented to test the gRPC client"""

from __future__ import print_function
from concurrent import futures
import time
import math
import logging
import sys
import os
import argparse
import signal

import grpc

import subprocess
import select
import threading


import nc_grpc_pb2
import nc_grpc_pb2_grpc


# global space
server_stop_flag = 0
server = None


class UserInputTimeoutError(Exception):
    pass

def print_data(request_iterator):
    try:
        # print("inside thread")
        prev_message = []
        for request_point in request_iterator:
            # print("inside requrest iterator")
            # print("Received %s " % (request_point.message))
            # response_str = (str(request_point.message).rstrip()).decode('ascii')
            print(str(request_point.message).rstrip())
            prev_message.append(str(request_point.message).rstrip())
    except:
        print("*********************client connection lost*********************")
        return

class NetconfRpcApi(nc_grpc_pb2_grpc.NetconfRpcApiServicer):
    """Provides methods that implement functionality of route guide server."""

    def GetExecuteCommand(self, request_iterator, context):

        t1 = threading.Thread(target=print_data, args=(request_iterator,))
        t1.start()
        # print("****************thread started****************")
        while True:
            cmd = '\n'
            # cmd = input()
            while (t1.isAlive()):
                i, o, e = select.select( [sys.stdin], [], [], 1 )
                if i:
                    cmd = sys.stdin.readline().strip()
                    break
                else:
                    pass

            cmd_new = str(cmd)

            if cmd == "<>":
                global server_stop_flag
                server_stop_flag = 1
            yield nc_grpc_pb2.RPCResponse(
                request_id = int(1),
                netconf_command = cmd_new)

    def InitialHandShake(self, request, context):
        global secret_key
        message_auth = request.message_req
        if message_auth == secret_key:
            print("Initial hand shake completed and the client is trusted")
            str = "client Auth successful"
            return nc_grpc_pb2.AuthResponse(
                message_res = str
            )
        else:
            return nc_grpc_pb2.AuthResponse(
                message_res = "client Auth failed"
            )

def serve():
    global port
    global server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    nc_grpc_pb2_grpc.add_NetconfRpcApiServicer_to_server(
        NetconfRpcApi(), server)

    with open('./server.key', 'rb') as f:
       private_key = f.read()
    with open('./server.crt', 'rb') as f:
       certificate_chain = f.read()
    server_credentials = grpc.ssl_server_credentials(((private_key, certificate_chain,),))
    server.add_secure_port('[::]:' + port, server_credentials)
    # server.add_insecure_port('[::]:50051')

    server.start()
    print("server started")
    server.wait_for_termination()


def signal_handler(sig, frame):
    global server

    print('entered into signal_handler')
    if server != None:
        server.stop(1)
    print("stopping the grpc server gracefully")
    pid = os.getpid()
    os.kill(pid, signal.SIGKILL)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)
    # signal.signal(signal.SIGKILL, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='client port',
                        required=True)
    args = parser.parse_args()
    secret_key = "nc_grpc_device"
    port = args.port
    logging.basicConfig()
    serve()
