'''
the entrance of the simulator
'''
import os
import numpy as np
from multiprocessing import Pool
import time
import afr_simulator
import skip_frame_simulator
import pause_encoder_simulator
import get_statistics
import argparse

def trace_loader(filename):
    f = open(filename, 'r')
    result_list = []
    pre_arrival_timestamp = 0
    arrival_interval_list = []
    decode_ts_list = []

    frames_amount = 0
    for line in f:
        cache2_ts = int(line.split(' ')[])
        decoding_time = int(line.split(' ')[])
        rtt = int(line.split(' ')[])
        arrival_timestamp = int(line.split(' ')[])
        total_ts = int(line.split(' ')[])
        decode_ts_list.append(total_ts)

        tmp_result_list = [arrival_timestamp, cache2_ts, decoding_time, rtt, total_ts]
        result_list.append(tmp_result_list)

        arrival_interval = arrival_timestamp - pre_arrival_timestamp
        arrival_interval_list.append(arrival_interval)
        pre_arrival_timestamp = arrival_timestamp
        frames_amount += 1

    return result_list


def start_simulator(filename, result_path):
    # print(filename)
    result_file = result_path+filename.split('/')[-1]+"_sim_traces.npy"

    if os.path.exists(result_file) == True:
        if os.path.getsize(result_file) == 0:
            os.remove(result_file)
            return 

        results_list = np.load(result_file, allow_pickle = True)
        default_traces = results_list[0]
        pure_skip_decode_offset_traces = results_list[1]
        pure_skip_decode_offset_other_skip_rate_traces = results_list[2]
        pause_encoder_traces = results_list[3]
        pause_encoder_threshold_2_traces = results_list[4]

        pause_encoder_sim = pause_encoder_simulator.pause_encoder_simulator()
        pause_encoder_traces = pause_encoder_sim.start(default_traces, queue_len_threshold = 1)
        pause_encoder_sim = pause_encoder_simulator.pause_encoder_simulator()
        pause_encoder_threshold_2_traces = pause_encoder_sim.start(default_traces, queue_len_threshold = 2)

        np.save(result_file, [default_traces, pure_skip_decode_offset_traces, pure_skip_decode_offset_other_skip_rate_traces, pause_encoder_traces, pause_encoder_threshold_2_traces])
        # # afr_w0_16_traces = afr_simulator.start(default_traces, w0=16)

    else:
        default_traces = trace_loader(filename) 
        if len(default_traces) == 0:
            return
        default_traces = default_traces[10:] # filter the IDR frame
        # afr_traces = afr_simulator.start(default_traces) # afr_traces[idx] = [arrival_timestamp, cache2_ts, decode_ts, rtt, total_ts, target_fps]
        
        pure_skip_simulator = skip_frame_simulator.pure_skip_simulator()
        pure_skip_decode_offset_traces = pure_skip_simulator.start(default_traces, decode_ts_offset=True)
        pure_skip_simulator = skip_frame_simulator.pure_skip_simulator()
        pure_skip_decode_offset_other_skip_rate_traces = pure_skip_simulator.start(default_traces, decode_ts_offset=True, skip_rate=0.25)
        pause_encoder_sim = pause_encoder_simulator.pause_encoder_simulator()
        pause_encoder_traces = pause_encoder_sim.start(default_traces, queue_len_threshold = 1)
        pause_encoder_sim = pause_encoder_simulator.pause_encoder_simulator()
        pause_encoder_threshold_2_traces = pause_encoder_sim.start(default_traces, queue_len_threshold = 2)

        # np.save(result_file, [default_traces, afr_traces, afr_no_delay_traces, pure_skip_traces])
        np.save(result_file, [default_traces, pure_skip_decode_offset_traces, pure_skip_decode_offset_other_skip_rate_traces, pause_encoder_traces, pause_encoder_threshold_2_traces])
    
    # get statistics
    if len(default_traces) == 0:
        return
    default_trace_evaluate_result = get_statistics.trace_evaluator(default_traces)
    pure_skip_decode_offset_result = get_statistics.trace_evaluator(pure_skip_decode_offset_traces)
    pure_skip_decode_offset_other_skip_rate_result = get_statistics.trace_evaluator(pure_skip_decode_offset_other_skip_rate_traces)
    pause_encoder_result = get_statistics.trace_evaluator(pause_encoder_traces)
    pause_encoder_threshold_2_result = get_statistics.trace_evaluator(pause_encoder_threshold_2_traces)
    result_list = [default_trace_evaluate_result, pure_skip_decode_offset_result,  pure_skip_decode_offset_other_skip_rate_result, pause_encoder_result, pause_encoder_threshold_2_result]
    return result_list    

if __name__ == "__main__":
    flow_info_path = ""
    logs_path = ""
    result_path = ""
    fnames = os.listdir(logs_path)

    parser = argparse.ArgumentParser()
    parser.add_argument('--ethernet', type=bool, default=False, help='the traces net type')
    args = parser.parse_args()
    fnames = os.listdir(logs_path)
    fnames_filtered = os.listdir(logs_path)

    if args.ethernet == True:
        filtered_sid = []
        result_path = ""
        netType = 2 # 2= ethernet , 3 = wifi
        # clientType = 0 # 0 = windowsPC, 2 = Mac
        with open(flow_info_path, 'r') as f:
            while True:
                line = f.readline().split()
                if not line:
                    break
                netCond = netType == int(line[4])
                # clientCond = clientType == int(line[6])
                if netCond:
                    filtered_sid.append(line[0])
        
        fnames_filtered = []
        for fname in fnames:
            sid = fname.split('_')[0]
            if sid in filtered_sid:
                fnames_filtered.append(fname)

    fnames = fnames_filtered
    print(len(fnames_filtered), '/', len(fnames))

    if args.testUnit != True: # running
        pool = Pool()
        results_list = []
        tmp_results_list = pool.starmap(start_simulator, [[logs_path+fname, result_path] for fname in fnames]) 
        valid_trace_cnt = 0
        for inner_list in tmp_results_list:
            if inner_list == None:
                continue
            results_list.append(inner_list)
            valid_trace_cnt += 1
        if args.ethernet == True:
            np.save("results/all_ethernet_traces_dist_info.npy", results_list)
        else:
            np.save("results/all_flow_traces_dist_info.npy", results_list)
        print("valid traces rate:", valid_trace_cnt/len(tmp_results_list), '/', valid_trace_cnt, '/', len(tmp_results_list))
        pool.close()
        pool.join()
