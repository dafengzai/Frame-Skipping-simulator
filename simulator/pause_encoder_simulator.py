import os
import numpy as np
import queue


class frame_info():
    def __init__(self, index, cache2_ts, decode_ts, rtt, arrival_timestamp):
        self.index = index
        self.cache2_ts = cache2_ts
        self.decode_ts = decode_ts
        self.rtt = rtt
        self.arrival_timestamp = arrival_timestamp

class pause_encoder_simulator:
    def __init__(self):
        self.pre_decoded_timestamp = 0
        self.pause_encoder_traces = []
        self.cache2_queue = queue.Queue()
        self.pause_command_queue = queue.Queue()
        self.queue_len_threshold = -1
        self.is_send_pause_command = False
        self.curr_pause_command = ["continue", 0]

    def check_pause_encoder_contoller(self, timestamp, rtt):
        qlen = self.cache2_queue.qsize()
        if qlen > self.queue_len_threshold:
            if self.is_send_pause_command == True:
                return
            # activate after 1 rtt
            activate_timestamp = timestamp + rtt
            pause_command = ["pause", activate_timestamp]
            self.pause_command_queue.put(pause_command)
            self.is_send_pause_command = True
        else:
            if self.is_send_pause_command == True:
                activate_timestamp = timestamp + rtt
                pause_command = ["continue", activate_timestamp]
                self.pause_command_queue.put(pause_command)
                self.is_send_pause_command = False


    def start(self, traces, queue_len_threshold = 1):

        self.queue_len_threshold = queue_len_threshold

        self.pre_decoded_timestamp = traces[0][0] + traces[0][1] + traces[0][2] 
        _frame_info = frame_info(0, 0, traces[0][2], traces[0][3], traces[0][0])
        self.cache2_queue.put(_frame_info) 

        default_traces_global_index = 0
        decoder_rtt_index = 0
        trace_len = len(traces)

        for idx in range(1, trace_len):
            arrival_timestamp = traces[idx][] 
            
            # CPU time slicing delay counted in decoding delay
            timeslice_diff =traces[idx][] - max(((traces[idx-1][] + traces[idx-1][] + traces[idx-1][]) - traces[idx][]), 0) # cpu_slicing = cache2 - (pre_decode_time - arrval_timestamp)
            timeslice_diff = max(timeslice_diff, 0)
            decode_ts = traces[idx][2]
            rtt = traces[idx][3]

            _frame_info = frame_info(idx, timeslice_diff, decode_ts, rtt, arrival_timestamp)

            global_timestamp = arrival_timestamp
            
            while self.cache2_queue.empty() != True:
                if self.pre_decoded_timestamp <= global_timestamp: 
                    head_node = self.cache2_queue.get()

                    if head_node.index == 0: # first video frame
                        self.pause_encoder_traces.append(traces[0])
                        continue
                    
                    cpu_timeslice = head_node.cache2_ts
                    cache2_ts = max(self.pre_decoded_timestamp - head_node.arrival_timestamp + cpu_timeslice, 0)

                    send_decoder_timestamp = head_node.arrival_timestamp + cache2_ts
                    while send_decoder_timestamp > traces[default_traces_global_index][0] + traces[default_traces_global_index][1]:
                        default_traces_global_index += 1
                        if default_traces_global_index == trace_len:
                            default_traces_global_index = trace_len - 1
                            break
                    default_send_decoder_timestamp = traces[default_traces_global_index][0] + traces[default_traces_global_index][1]
                    default_decode_ts = traces[default_traces_global_index][2]
                    default_pre_send_decoder_timestamp = traces[default_traces_global_index - 1][0] + traces[default_traces_global_index - 1][1]
                    default_pre_decode_ts = traces[default_traces_global_index - 1][2]
                    default_send_decoder_interval = default_send_decoder_timestamp - default_pre_send_decoder_timestamp
                    if default_send_decoder_interval > 0:
                        decode_ts = default_pre_decode_ts + (max(0, send_decoder_timestamp - default_pre_send_decoder_timestamp)/default_send_decoder_interval) * (default_decode_ts - default_pre_decode_ts)
                    else:
                        decode_ts = default_decode_ts

                    trace_element = [head_node.arrival_timestamp, cache2_ts, decode_ts, head_node.rtt, cache2_ts + decode_ts + head_node.rtt, head_node.index]
                    self.pause_encoder_traces.append(trace_element)
                    self.pre_decoded_timestamp = head_node.arrival_timestamp + cache2_ts + decode_ts
                    # pause encoder checking
                    while self.pre_decoded_timestamp > traces[decoder_rtt_index][0]:
                        decoder_rtt_index += 1
                        if decoder_rtt_index == trace_len:
                            decoder_rtt_index = trace_len - 1
                            break
                    default_arrival_timestamp = traces[decoder_rtt_index][0] 
                    default_rtt = traces[decoder_rtt_index][3]
                    default_pre_arrival_timestamp = traces[decoder_rtt_index - 1][0] 
                    default_pre_rtt = traces[decoder_rtt_index - 1][3]
                    default_arrival_interval = default_arrival_timestamp - default_pre_arrival_timestamp
                    if default_arrival_interval > 0:
                        curr_rtt = default_pre_rtt + (max(0, self.pre_decoded_timestamp - default_pre_arrival_timestamp)/default_arrival_interval) * (default_rtt - default_pre_rtt)
                    else:
                        curr_rtt = default_rtt
                    self.check_pause_encoder_contoller(self.pre_decoded_timestamp, curr_rtt)


                else: # decoding
                    break
            
            while self.pause_command_queue.empty() != True: 
                fisrt_command = self.pause_command_queue.queue[0]
                if fisrt_command[1] <= arrival_timestamp: # change activate
                    self.curr_pause_command = self.pause_command_queue.get()
                else:
                    break

            if self.curr_pause_command[0] == "continue":
                self.cache2_queue.put(_frame_info)

            self.check_pause_encoder_contoller(arrival_timestamp, rtt)
                      

            
        return self.pause_encoder_traces