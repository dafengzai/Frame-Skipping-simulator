import os
import numpy as np
import queue
import math
import random

class frame_info():
    def __init__(self, index, cpu_timeslice, decode_ts, rtt, arrival_timestamp):
        self.index = index
        self.cpu_timeslice = cpu_timeslice
        self.decode_ts = decode_ts
        self.rtt = rtt
        self.arrival_timestamp = arrival_timestamp
        self.cache2_ts = 5
        self.predict_rtt = 20 
        self.predict_decoded_timestamp = 0
        self.predict_decoded_delay = 50
        self.delay_capacity = 0

class pure_skip_simulator:
    def __init__(self):
        self.pre_decoded_timestamp = 0
        self.decode_ts_offset = False
        self.pure_skip_traces = []
        self.traces = []
        # for decode_ts offset
        self.default_traces_global_index = 0 
    
    def send_frame_to_decoder(self, head_node):
        cache2_ts = max(self.pre_decoded_timestamp - head_node.arrival_timestamp + head_node.cpu_timeslice, 0)
        if self.decode_ts_offset == True: 
            send_decoder_timestamp = head_node.arrival_timestamp + cache2_ts
            while send_decoder_timestamp > self.traces[self.default_traces_global_index][0] + self.traces[self.default_traces_global_index][1]:
                self.default_traces_global_index += 1
                
            default_send_decoder_timestamp = self.traces[self.default_traces_global_index][0] + self.traces[self.default_traces_global_index][1]
            default_decode_ts = self.traces[self.default_traces_global_index][2]
            default_pre_send_decoder_timestamp = self.traces[self.default_traces_global_index - 1][0] + self.traces[self.default_traces_global_index - 1][1]
            default_pre_decode_ts = self.traces[self.default_traces_global_index - 1][2]
            default_send_decoder_interval = default_send_decoder_timestamp - default_pre_send_decoder_timestamp
            if default_send_decoder_interval > 0:
                head_node.decode_ts = default_pre_decode_ts + (max(0, send_decoder_timestamp - default_pre_send_decoder_timestamp)/default_send_decoder_interval) * (default_decode_ts - default_pre_decode_ts)
            else:
                head_node.decode_ts = default_decode_ts

        self.pure_skip_traces.append([head_node.arrival_timestamp, cache2_ts, head_node.decode_ts, head_node.rtt, \
            cache2_ts + head_node.decode_ts + head_node.rtt, head_node.index]) # self.pure_skip_traces[idx] = [arrival_timestamp, cache2_ts, decoding_time, rtt, total_ts]
        self.pre_decoded_timestamp = head_node.arrival_timestamp + cache2_ts + head_node.decode_ts


    def start(self, traces, decode_ts_offset = True, skip_rate = 0.5):
        # traces[idx] = [arrival_timestamp, cache2_ts, decoding_time, rtt, total_ts]
        if decode_ts_offset == True:
            self.decode_ts_offset = True
        self.traces = traces

        cache2_queue = queue.Queue()

        self.pre_decoded_timestamp = traces[0][0] + traces[0][1] + traces[0][2] 
        _frame_info = frame_info(0, 0, traces[0][2], traces[0][3], traces[0][0])
        cache2_queue.put(_frame_info)

        for idx in range(1, len(traces)):
            arrival_timestamp = traces[idx][0] 
            
            # CPU time slicing delay counted in decoding delay
            timeslice_diff =traces[idx][1] - max(((traces[idx-1][0] + traces[idx-1][1] + traces[idx-1][2]) - traces[idx][0]), 0) # cpu_slicing = cache2 - (pre_decode_time - arrval_timestamp)
            timeslice_diff = max(timeslice_diff, 0)

            decode_ts = traces[idx][2]
            rtt = traces[idx][3]

            _frame_info = frame_info(idx, timeslice_diff, decode_ts, rtt, arrival_timestamp)

            global_timestamp = arrival_timestamp
            cache2_queue.put(_frame_info)
            
            # dequeuing
            while cache2_queue.empty() != True:
                if self.pre_decoded_timestamp <= global_timestamp: 
                    head_node = cache2_queue.get()

                    if head_node.index == 0: #first vedio frame
                        self.pure_skip_traces.append(traces[0])

                    elif cache2_queue.empty() == True:
                        self.send_frame_to_decoder(head_node)

                    else:
                        skip_num = 1/(1-skip_rate)
                        skip_diff = (skip_num-int(skip_num))
                        if skip_diff == 0:
                            skip_diff = 1
                        random_rate = random.random()
                        if random_rate <= skip_diff:
                            second_node = cache2_queue.get()
                            if (head_node.index % 2) == 1: # base_layer
                                self.send_frame_to_decoder(head_node)
                            else:
                                self.send_frame_to_decoder(second_node)
                        else:
                            self.send_frame_to_decoder(head_node)

                else: # decoding
                    break        
        return self.pure_skip_traces