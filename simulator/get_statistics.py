'''
get the statistics based on traces
'''
import numpy as np
import os

dist_len = 300


def trace_evaluator(trace, monitor_offset=4): # default 4ms monitor_offset of render refresh time
    decoder_queue_ts_dist = [0 for _ in range(dist_len)]
    total_ts_dist = [0 for _ in range(dist_len)]
    valid_fps_num_dist = [0 for _ in range(51)] # 20fps to 70fps
    rare_fps_num_dist = [0 for _ in range(51)]
    valid_fps_rate_dist = [0 for _ in range(101)] # 0.5 to 1.0 step of 0.005

    # fps calculate
    first_final_timestamp = trace[0][0] + trace[0][1] + trace[0][2]
    monitor_refresh_interval = (1/60) * 1000
    monitor_refresh_time = first_final_timestamp + monitor_offset
    monitor_update_times = 0 # update 60 times means 1 second

    decode_ts_list = []

    decode_q_ts = -1
    total_ts = -1
    valid_frames_cnt = 0
    frames_cnt = 0
    for idx in range(len(trace)):
        final_timestamp = trace[idx][0] + trace[idx][1] + trace[idx][2]
        while final_timestamp > monitor_refresh_time: # monitor refresh
            valid_frames_cnt += is_valid_frame
            is_valid_frame = 0
            # delay info
            if decode_q_ts != -1: # not caculated yet
                decoder_queue_ts_dist[decode_q_ts] += 1
                total_ts_dist[total_ts] += 1
                decode_q_ts = -1
            # get fps info
            if monitor_update_times == 60:
                monitor_update_times = 0
                if frames_cnt >= 20: # Not frame loss
                    valid_fps_num_dist[min(max(valid_frames_cnt-20, 0), 50)] += 1
                    rare_fps_num_dist[min(max(frames_cnt-20, 0), 50)] += 1
                    valid_fps_rate = valid_frames_cnt/frames_cnt
                    valid_fps_rate_dist[int(max(valid_fps_rate-0.5, 0.5)/0.005)] += 1
                valid_frames_cnt = 0
                frames_cnt = 0

            monitor_update_times += 1
            monitor_refresh_time += monitor_refresh_interval
            

        decode_q_ts = int(trace[idx][1])
        if decode_q_ts > dist_len - 1:
            decode_q_ts = dist_len - 1

        decode_ts = int(trace[idx][2])
        decode_ts_list.append(decode_ts)

        total_ts = int(trace[idx][4])
        if total_ts < 0: # error log
            total_ts = 0
        if total_ts > dist_len - 1:
            total_ts = dist_len - 1

        frames_cnt += 1
        is_valid_frame = 1


    mean_decode_ts = np.mean(decode_ts_list)

    if sum(rare_fps_num_dist) == 0:
        return

    result_list = [decoder_queue_ts_dist, total_ts_dist, valid_fps_num_dist, rare_fps_num_dist, valid_fps_rate_dist, len(trace), int(mean_decode_ts)]
    return result_list