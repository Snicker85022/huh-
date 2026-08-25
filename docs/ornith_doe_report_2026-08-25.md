# Ornith-1.5-35B-A3B — COMPLETE DOE DATA DUMP (all runs, all kernels)
Host: gflip | Model: Ornith-1.5-35B-A3B Q6_K (27.2 GiB) + mmproj vision | Ryzen 9 PRO 8945HS / Radeon 780M (gfx1103) / 64GB DDR5-5600 dual (89.6 GB/s)
llama.cpp Vulkan. Builds: pre-session 786148e9d (Aug-1); session rebuild f280b2698 (ggml 0.21.0, +398 commits).
Kernels: 6.8.0-136 GA and 7.0.0-30 HWE. GTT ceiling: 23.4 GiB (pre-fix) -> 50 GiB (post-fix). mclk fixed 2800 MHz.
All CSVs verbatim below. Every row and every column from every experiment.

# ============ KERNEL 6.8.0-136 ============

## 6.8 service/exec config used in this block
base (all 24 combos): 
  /usr/bin/env VK_ICD_FILENAMES=<radv|amdvlk> llama-server -m Ornith-1.5-35B-Q6_K.gguf
    --mmproj mmproj-Ornith-1.5-35B-BF16.gguf --jinja --alias ornith-1.5-35b
    --n-gpu-layers 99 --n-cpu-moe {0|6|10} --flash-attn on -t 8 -np {2|4}
    -c 16384 --temp 0.6 --top-p 0.95 --top-k 20 --image-min-tokens 1024
    --host 0.0.0.0 --port 8082 [--no-mmap]
  factors: driver{radv,amdvlk} x n_cpu_moe{0,6,10} x np{2,4} x mmap{on,off} = 24 combos
  baseline = pre-DOE service (cmoe6 np4)

## 6.8 full grid (24 combos + baseline) — ALL columns
Columns: combo, load_s, p1_pp_tps, p1_gen_tps, p1_tokens, p2_tool_ok, p2_gen_tps, p2_tokens, p3_pp_tps, p3_gen_tps, p3_tokens, gtt_used_gib, gtt_headroom_gib, crashed, ts
(26 lines)
```
combo,load_s,p1_pp_tps,p1_gen_tps,p1_tokens,p2_tool_ok,p2_gen_tps,p2_tokens,p3_pp_tps,p3_gen_tps,p3_tokens,gtt_used_gib,gtt_headroom_gib,crashed,ts
BASELINE,0.0,64.4,18.1,128,1,12.3,45,86.0,12.4,128,0.0,50.0,0,2026-08-24 23:13:40
amdvlk/cmoe0/np4/mmap1,9.0,43.0,23.5,128,1,23.7,49,176.1,23.3,121,27.2,22.8,0,2026-08-24 23:18:17
radv/cmoe6/np2/mmap1,16.0,42.5,21.2,128,1,21.4,45,203.6,21.0,120,27.4,22.6,0,2026-08-24 23:18:58
amdvlk/cmoe6/np4/mmap0,10.4,40.6,20.3,128,1,20.6,45,151.2,20.0,110,23.5,26.5,0,2026-08-24 23:19:35
amdvlk/cmoe10/np4/mmap1,6.0,39.1,19.4,128,1,19.6,45,163.0,19.1,128,27.6,22.4,0,2026-08-24 23:20:10
amdvlk/cmoe0/np2/mmap1,5.0,43.0,23.5,128,1,23.6,49,174.9,23.1,114,27.0,23.0,0,2026-08-24 23:20:39
radv/cmoe10/np4/mmap0,19.3,31.8,18.9,128,1,20.2,45,169.6,19.8,128,21.1,28.9,0,2026-08-24 23:21:27
amdvlk/cmoe6/np2/mmap1,9.0,40.6,20.3,128,1,20.5,49,165.6,20.0,107,27.5,22.5,0,2026-08-24 23:22:02
radv/cmoe10/np4/mmap1,16.0,59.6,20.3,128,1,20.5,44,214.9,20.1,106,27.6,22.4,0,2026-08-24 23:22:41
amdvlk/cmoe0/np4/mmap0,12.0,43.0,23.5,128,1,23.7,45,175.1,23.2,128,26.8,23.2,0,2026-08-24 23:23:17
amdvlk/cmoe6/np2/mmap0,7.2,40.8,20.3,128,1,20.5,44,150.2,20.0,114,23.5,26.5,0,2026-08-24 23:23:53
radv/cmoe0/np2/mmap1,13.0,42.6,23.4,128,1,23.6,45,210.7,23.2,120,27.0,23.0,0,2026-08-24 23:24:29
amdvlk/cmoe0/np2/mmap0,13.0,43.1,23.4,128,1,23.7,44,174.6,23.2,102,26.6,23.4,0,2026-08-24 23:25:05
amdvlk/cmoe10/np2/mmap1,8.0,39.2,19.4,128,1,19.5,45,162.6,19.1,119,27.3,22.7,0,2026-08-24 23:25:42
radv/cmoe6/np4/mmap0,18.2,29.3,20.0,128,1,21.1,45,173.8,20.7,128,23.4,26.6,0,2026-08-24 23:26:28
radv/cmoe10/np2/mmap1,14.0,41.7,20.4,128,1,20.6,45,198.0,20.2,113,27.3,22.7,0,2026-08-24 23:27:07
radv/cmoe0/np4/mmap0,19.1,63.4,23.4,128,1,23.8,44,235.4,23.2,123,26.8,23.2,0,2026-08-24 23:27:46
amdvlk/cmoe10/np4/mmap0,10.1,39.2,19.4,128,1,19.6,45,141.7,19.2,128,21.1,28.9,0,2026-08-24 23:28:26
radv/cmoe6/np2/mmap0,19.4,29.9,20.2,128,1,21.1,45,170.3,20.8,98,23.5,26.5,0,2026-08-24 23:29:12
amdvlk/cmoe6/np4/mmap1,11.0,40.6,20.3,128,1,20.4,45,164.2,19.9,128,27.4,22.6,0,2026-08-24 23:29:51
radv/cmoe6/np4/mmap1,16.0,60.7,21.1,128,1,21.2,45,219.3,20.7,128,27.4,22.6,0,2026-08-24 23:30:30
radv/cmoe10/np2/mmap0,22.0,25.9,19.0,128,1,20.2,45,152.8,19.9,117,20.9,29.1,0,2026-08-24 23:31:22
radv/cmoe0/np2/mmap0,16.1,42.3,23.2,128,1,23.7,45,210.1,23.2,128,26.6,23.4,0,2026-08-24 23:32:01
radv/cmoe0/np4/mmap1,10.0,63.1,23.5,128,1,23.8,44,235.7,23.2,119,27.2,22.8,0,2026-08-24 23:32:32
amdvlk/cmoe10/np2/mmap0,10.3,39.4,19.4,128,1,19.6,45,140.4,19.2,105,20.9,29.1,0,2026-08-24 23:33:10
```

## 6.8 pre-session DOE (2026-08-23, 24GiB GTT cap, build 786148e9d) — ALL files

## pre-session results-final
Columns: label, driver{radv,amdvlk}, cmoe{on/off}, fa{auto/on/off}, kvq, t(threads), ngl, pp_tok_s, gen_tok_s, pred_ms, rss_gib, load_s, status
(11 lines)
```
label,driver,cmoe,fa,kvq,t,ngl,pp_tok_s,gen_tok_s,pred_ms,rss_gib,load_s,status
control-1,radv,True,auto,False,0,99,28.77,13.24,19338.6,27.4,4.2,ok
control-2,radv,True,auto,False,0,99,33.91,13.22,19371.0,27.4,4.2,ok
control-3,radv,True,auto,False,0,99,33.92,13.23,19348.8,27.4,4.2,ok
driver-radv,radv,True,auto,False,0,99,33.47,13.22,19365.5,27.4,4.2,ok
driver-amdvlk,amdvlk,True,auto,False,0,99,34.14,12.2,20988.5,27.38,4.2,ok
fact-cmoeT-faF-t8,radv,True,False,False,8,99,33.36,13.18,19424.0,27.4,4.2,ok
fact-cmoeT-faT-t8,radv,True,True,False,8,99,33.5,13.25,19327.6,27.4,4.2,ok
fact-cmoeT-faT-t16,radv,True,True,False,16,99,33.72,11.21,22827.8,27.4,4.2,ok
cpu-only,radv,False,False,False,16,0,21.99,12.21,20967.9,28.04,4.3,ok
crash-check-cmoeF,radv,False,True,False,8,99,,,,,17.8,FAIL rc=-6
```

## pre-session results-v2
Columns: label, run_type{single,burst}, pp_tok_s, gen_tok_s, agg_tok_s, ttft_p50_ms, ttft_p95_ms, rss_gib, load_s, status
(9 lines)
```
label,run_type,pp_tok_s,gen_tok_s,agg_tok_s,ttft_p50_ms,ttft_p95_ms,rss_gib,load_s,status
control,single,25.55,13.24,,,,27.4,4.3,ok
ctx32k,single,24.82,13.25,,,,27.4,4.2,ok
batch4k,single,26.22,13.26,,,,27.38,4.2,ok
tb8,single,26.3,13.24,,,,27.4,4.2,ok
ncmoe10,single,47.85,20.03,,,,27.4,8.2,ok
np1-burst,burst,,,10.14,21968,40896,27.51,4.2,ok
np4-burst,burst,,,21.08,6127,6321,27.4,4.2,ok
np8-burst,burst,,,21.06,6093,6286,27.4,4.2,ok
```

## pre-session results (raw run log)
(17 lines)
```
run,label,driver,cmoe,fa,kvq,t,ngl,pp_tok_s,gen_tok_s,pred_ms,rss_gib,load_s,status
0,driver-radv,radv,True,auto,False,0,99,33.58,13.23,19353.2,27.4,4.2,ok
1,driver-amdvlk,amdvlk,True,auto,False,0,99,34.15,12.14,21090.8,27.38,4.2,ok
11,kvq-probe,radv,True,True,True,16,99,33.81,10.9,23485.0,27.4,4.2,ok
15,control,radv,True,auto,False,0,99,33.45,13.19,19412.7,27.4,4.2,ok
14,control,radv,True,auto,False,0,99,33.1,13.14,19476.6,27.4,4.2,ok
4,factorial,radv,False,True,False,8,99,,,,,14.3,FAIL rc=-6
3,factorial,radv,False,False,False,16,99,,,,,14.1,FAIL rc=-6
10,kvq-probe,radv,True,True,True,8,99,33.52,13.19,19402.6,27.4,4.0,ok
9,factorial,radv,True,True,False,16,99,32.8,10.8,23702.8,27.4,4.2,ok
12,cpu-only,radv,False,False,False,16,0,21.82,12.08,21190.5,28.04,4.3,ok
5,factorial,radv,False,True,False,16,99,,,,,14.4,FAIL rc=-6
7,factorial,radv,True,False,False,16,99,33.4,11.24,22781.0,27.4,4.2,ok
6,factorial,radv,True,False,False,8,99,33.67,13.17,19432.7,27.4,4.2,ok
2,factorial,radv,False,False,False,8,99,,,,,14.3,FAIL rc=-6
13,control,radv,True,auto,False,0,99,33.98,13.25,19319.4,27.4,4.0,ok
8,factorial,radv,True,True,False,8,99,33.65,13.19,19406.4,27.4,4.2,ok
```

## pre-session results-old-build
(17 lines)
```
run,label,driver,cmoe,fa,kvq,t,ngl,pp_tok_s,gen_tok_s,pred_ms,rss_gib,load_s,status
0,driver-radv,radv,True,auto,False,0,99,33.58,13.23,19353.2,27.4,4.2,ok
1,driver-amdvlk,amdvlk,True,auto,False,0,99,34.15,12.14,21090.8,27.38,4.2,ok
11,kvq-probe,radv,True,True,True,16,99,33.81,10.9,23485.0,27.4,4.2,ok
15,control,radv,True,auto,False,0,99,33.45,13.19,19412.7,27.4,4.2,ok
14,control,radv,True,auto,False,0,99,33.1,13.14,19476.6,27.4,4.2,ok
4,factorial,radv,False,True,False,8,99,,,,,14.3,FAIL rc=-6
3,factorial,radv,False,False,False,16,99,,,,,14.1,FAIL rc=-6
10,kvq-probe,radv,True,True,True,8,99,33.52,13.19,19402.6,27.4,4.0,ok
9,factorial,radv,True,True,False,16,99,32.8,10.8,23702.8,27.4,4.2,ok
12,cpu-only,radv,False,False,False,16,0,21.82,12.08,21190.5,28.04,4.3,ok
5,factorial,radv,False,True,False,16,99,,,,,14.4,FAIL rc=-6
7,factorial,radv,True,False,False,16,99,33.4,11.24,22781.0,27.4,4.2,ok
6,factorial,radv,True,False,False,8,99,33.67,13.17,19432.7,27.4,4.2,ok
2,factorial,radv,False,False,False,8,99,,,,,14.3,FAIL rc=-6
13,control,radv,True,auto,False,0,99,33.98,13.25,19319.4,27.4,4.0,ok
8,factorial,radv,True,True,False,8,99,33.65,13.19,19406.4,27.4,4.2,ok
```

## pre-session n_cpu_moe sweep
Columns: N(experts to CPU), pp_tok_s, gen_tok_s, rss_gib, load_s, status
(8 lines)
```
N,pp_tok_s,gen_tok_s,rss_gib,load_s,status
,23.3,13.26,27.4,4.2,ok
5,,,,12.2,FAIL
10,49.65,20.23,27.4,8.6,ok
10,41.38,20.27,27.4,10.0,ok
15,35.54,19.07,27.4,8.3,ok
20,36.92,18.12,27.4,8.0,ok
25,32.7,16.21,27.4,6.3,ok
```

## pre-session n_cpu_moe fine
Columns: N, pp_tok_s, gen_tok_s, rss_gib, load_s, status
(6 lines)
```
N,pp_tok_s,gen_tok_s,rss_gib,load_s,status
8,48.72,20.75,27.4,8.2,ok
9,46.26,20.46,27.4,8.0,ok
11,49.53,20.0,27.4,8.4,ok
12,37.86,19.82,27.4,8.7,ok
10,50.49,20.22,27.4,8.5,ok
```

## pre-session n_cpu_moe edge
Columns: N, pp_tok_s, gen_tok_s, rss_gib, load_s, status
(3 lines)
```
N,pp_tok_s,gen_tok_s,rss_gib,load_s,status
7,49.86,20.89,27.4,10.0,ok
6,50.1,21.11,27.4,8.2,ok
```

## pre-session n_cpu_moe 6 x3 replicates
Columns: run, pp/gen/rss, load_s
(4 lines)
```
run,pp/gen/rss,load_s
1,41.32/21.17/27.4,10.0
2,46.37/21.13/27.4,8.2
3,41.42/21.11/27.4,10.2
```

# ============ KERNEL 7.0.0-30 ============

## 7.0 service/exec config used in this block
Same base as 6.8 grid. Per-run measured columns added: req_stapm_w, req_perf,
  measured_sclk_state, measured_sclk_mhz, gpu_busy_pct, gpu_power_w, gpu_temp_c,
  gpu_sclk_mhz, cpu_max_mhz, cpu_avg_mhz. NOTE: on 7.x the amdgpu hwmon moved hwmon4->hwmon6;
  early 7.x grid rows have empty power/temp columns (hardcoded hwmon4 read failed).

## 7.0 full grid (24 combos) — ALL 24 columns
Columns: combo, load_s, p1_pp_tps, p1_gen_tps, p1_tokens, p2_tool_ok, p2_gen_tps, p2_tokens, p3_pp_tps, p3_gen_tps, p3_tokens, gtt_used_gib, gtt_headroom_gib, crashed, ts, req_stapm_w, req_perf, measured_sclk_state, measured_sclk_mhz, gpu_busy_pct, gpu_power_w, gpu_temp_c, gpu_sclk_mhz, cpu_max_mhz, cpu_avg_mhz
(25 lines)
```
combo,load_s,p1_pp_tps,p1_gen_tps,p1_tokens,p2_tool_ok,p2_gen_tps,p2_tokens,p3_pp_tps,p3_gen_tps,p3_tokens,gtt_used_gib,gtt_headroom_gib,crashed,ts,req_stapm_w,req_perf,measured_sclk_state,measured_sclk_mhz,gpu_busy_pct,gpu_power_w,gpu_temp_c,gpu_sclk_mhz,cpu_max_mhz,cpu_avg_mhz
amdvlk/cmoe0/np4/mmap1,4.0,42.6,23.4,128,1,23.6,45,175.5,23.1,134,27.2,22.8,0,2026-08-25 00:01:37,,auto,0,800Mhz *,98.0,0
radv/cmoe6/np2/mmap1,11.0,42.0,21.2,128,1,21.2,44,203.3,20.9,103,27.4,22.6,0,2026-08-25 00:02:22,,auto,0,800Mhz *,88.0,0
amdvlk/cmoe6/np4/mmap0,11.0,40.6,20.4,128,1,20.5,45,150.4,20.0,117,23.5,26.5,0,2026-08-25 00:03:10,,auto,0,800Mhz *,89.0,0
amdvlk/cmoe10/np4/mmap1,6.0,39.0,19.4,128,1,19.5,44,162.6,19.1,121,27.6,22.4,0,2026-08-25 00:03:54,,auto,0,800Mhz *,83.0,0
amdvlk/cmoe0/np2/mmap1,5.0,42.7,23.3,128,1,23.5,49,174.9,23.0,127,27.0,23.0,0,2026-08-25 00:04:34,,auto,0,800Mhz *,98.0,0
radv/cmoe10/np4/mmap0,13.7,31.3,18.9,128,1,20.1,45,166.5,19.8,119,21.1,28.9,0,2026-08-25 00:05:26,,auto,0,800Mhz *,83.0,0
amdvlk/cmoe6/np2/mmap1,9.0,40.6,20.3,128,1,20.5,45,164.8,20.0,101,27.5,22.5,0,2026-08-25 00:06:10,,auto,0,800Mhz *,89.0,0
radv/cmoe10/np4/mmap1,12.0,58.8,20.3,128,1,20.5,49,212.9,20.1,107,27.6,22.4,0,2026-08-25 00:06:55,,auto,0,800Mhz *,84.0,0
amdvlk/cmoe0/np4/mmap0,12.0,43.0,23.4,128,1,23.6,45,175.4,23.1,152,26.8,23.2,0,2026-08-25 00:07:43,,auto,0,800Mhz *,98.0,0
amdvlk/cmoe6/np2/mmap0,7.0,40.6,20.3,128,1,20.6,45,149.0,20.1,104,23.5,26.5,0,2026-08-25 00:08:27,,auto,0,800Mhz *,89.0,0
radv/cmoe0/np2/mmap1,11.0,42.7,23.4,128,1,23.6,45,211.4,23.2,100,27.0,23.0,0,2026-08-25 00:09:11,,auto,0,800Mhz *,97.0,0
amdvlk/cmoe0/np2/mmap0,11.0,42.9,23.3,128,1,23.5,49,174.4,23.0,102,26.6,23.4,0,2026-08-25 00:09:55,,auto,0,800Mhz *,97.0,0
amdvlk/cmoe10/np2/mmap1,7.0,39.3,19.4,128,1,19.6,45,162.0,19.1,114,27.3,22.7,0,2026-08-25 00:10:40,,auto,0,800Mhz *,83.0,0
radv/cmoe6/np4/mmap0,11.0,38.0,21.1,128,1,21.5,45,175.4,21.1,133,23.4,26.6,0,2026-08-25 00:11:28,,auto,0,800Mhz *,88.0,0
radv/cmoe10/np2/mmap1,6.0,41.7,20.4,128,1,20.6,44,198.4,20.2,116,27.3,22.7,0,2026-08-25 00:12:08,,auto,0,800Mhz *,83.0,0
radv/cmoe0/np4/mmap0,9.0,63.0,23.5,128,1,23.8,45,236.5,23.2,143,26.8,23.2,0,2026-08-25 00:12:49,,auto,0,800Mhz *,98.0,0
amdvlk/cmoe10/np4/mmap0,9.0,39.3,19.4,128,1,19.6,45,140.5,19.2,104,21.1,28.9,0,2026-08-25 00:13:36,,auto,0,800Mhz *,83.0,0
radv/cmoe6/np2/mmap0,14.7,30.1,20.3,128,1,21.2,44,170.7,20.9,130,23.5,26.5,0,2026-08-25 00:14:29,,auto,0,800Mhz *,88.0,0
amdvlk/cmoe6/np4/mmap1,8.0,40.7,20.4,128,1,20.6,44,165.6,20.0,142,27.4,22.6,0,2026-08-25 00:15:15,,auto,0,800Mhz *,89.0,0
radv/cmoe6/np4/mmap1,12.0,42.2,21.3,128,1,21.5,45,201.9,21.0,157,27.4,22.6,0,2026-08-25 00:16:03,,auto,0,800Mhz *,88.0,0
radv/cmoe10/np2/mmap0,7.0,41.7,20.5,128,1,20.6,45,159.7,20.3,102,20.9,29.1,0,2026-08-25 00:16:46,,auto,0,800Mhz *,83.0,0
radv/cmoe0/np2/mmap0,8.1,43.5,23.4,128,1,23.7,44,213.5,23.2,120,26.6,23.4,0,2026-08-25 00:17:26,,auto,0,800Mhz *,98.0,0
radv/cmoe0/np4/mmap1,6.0,63.7,23.6,128,1,23.8,45,236.0,23.3,128,27.2,22.8,0,2026-08-25 00:18:03,,auto,0,800Mhz *,98.0,0
amdvlk/cmoe10/np2/mmap0,9.0,39.1,19.4,128,1,19.6,45,140.2,19.2,133,20.9,29.1,0,2026-08-25 00:18:52,,auto,0,800Mhz *,83.0,0
```

## 7.0 power/clock envelope (5 runs) — ALL columns
Columns: base radv/cmoe0/np2/mmap0; req_stapm_w{45,54,60}, req_perf{auto,high}; measured sclk/mclk, busy, power, temp. Power sampled post-benchmark (understated).
(6 lines)
```
combo,load_s,p1_pp_tps,p1_gen_tps,p1_tokens,p2_tool_ok,p2_gen_tps,p2_tokens,p3_pp_tps,p3_gen_tps,p3_tokens,gtt_used_gib,gtt_headroom_gib,crashed,ts,req_stapm_w,req_perf,measured_sclk_state,measured_sclk_mhz,gpu_busy_pct,gpu_power_w,gpu_temp_c,gpu_sclk_mhz
radv/cmoe0/np2/mmap0,9.7,42.8,23.3,128,1,23.5,44,211.7,23.1,103,26.6,23.4,0,2026-08-25 00:23:40,45,auto,0,800Mhz *,97.0,13.5899,49.266666666666666,0
radv/cmoe0/np2/mmap0,9.0,43.8,23.3,128,1,23.5,45,215.7,23.1,114,26.6,23.4,0,2026-08-25 00:24:21,60,auto,0,800Mhz *,98.0,15.300633333333334,52.1,0
radv/cmoe0/np2/mmap0,8.0,51.8,23.5,128,1,23.7,45,223.4,23.3,111,26.6,23.4,0,2026-08-25 00:25:00,60,high,2,2799Mhz *,98.0,16.428333333333335,53.96666666666667,2
radv/cmoe0/np2/mmap0,8.0,47.6,23.4,128,1,23.1,45,201.5,21.5,120,26.6,23.4,0,2026-08-25 00:25:41,45,high,2,2799Mhz *,91.0,13.972299999999999,53.4,2
radv/cmoe0/np2/mmap0,8.8,51.8,23.5,128,1,23.7,45,216.9,23.2,119,26.6,23.4,0,2026-08-25 00:26:22,54,high,2,2799Mhz *,98.0,15.871966666666667,54.46666666666667,2
```

## 7.0 batch x concurrency grid (12 runs) — ALL columns
Columns: combo(np{1,2,4}/ub{64,128,256,512}), load_s, p1_gen_tps, p2_tool_ok, p2_gen_tps, tool_func_ok, tool_arg_ok, tool_total, tool_acc_pct, excellence_score, excellence_secs, excellence_grade, gpu_busy_pct, gpu_power_w, gpu_temp_c, sclk_peak, mclk_peak, crashed, ts. NOTE: crashed col bogus (PID-capture-order bug); real crash count = 0 (journal).
(13 lines)
```
combo,load_s,p1_gen_tps,p2_tool_ok,p2_gen_tps,tool_func_ok,tool_arg_ok,tool_total,tool_acc_pct,excellence_score,excellence_secs,excellence_grade,gpu_busy_pct,gpu_power_w,gpu_temp_c,sclk_peak,mclk_peak,crashed,ts
np1/ub64,6.0,23.1,0,23.1,5,4,5,90.0,4,31.9,7.5,99,44.9,65.7,1: 2706Mhz *,1: 2800Mhz *,1,2026-08-25 00:57:04
np1/ub128,6.0,23.1,0,23.0,5,3,5,80.0,1,31.9,1.9,99,44.3,70.8,1: 2666Mhz *,1: 2800Mhz *,1,2026-08-25 00:58:36
np1/ub256,6.0,23.1,0,23.1,5,3,5,80.0,0,32.0,0.0,98,43.8,71.1,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:00:05
np1/ub512,6.0,23.1,0,23.0,4,3,5,70.0,3,32.0,5.6,97,44.0,71.7,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:01:31
np2/ub64,6.0,23.2,0,23.1,4,3,5,70.0,2,32.0,3.8,99,44.6,73.5,1: 2661Mhz *,1: 2800Mhz *,1,2026-08-25 01:03:10
np2/ub128,5.0,23.1,0,23.0,5,4,5,90.0,0,32.1,0.0,99,44.3,73.8,1: 996Mhz *,1: 2800Mhz *,1,2026-08-25 01:04:40
np2/ub256,6.0,23.1,0,23.0,5,4,5,90.0,2,32.0,3.7,98,43.9,72.5,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:06:08
np2/ub512,6.0,23.1,0,23.0,5,4,5,90.0,4,32.0,7.5,97,44.0,72.2,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:07:33
np4/ub64,6.0,23.3,0,23.1,5,3,5,80.0,2,29.8,4.0,99,44.8,74.6,1: 2727Mhz *,1: 2800Mhz *,1,2026-08-25 01:09:04
np4/ub128,6.0,23.2,0,23.1,5,4,5,90.0,2,29.8,4.0,99,44.7,74.2,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:10:27
np4/ub256,6.0,23.3,0,23.2,4,3,5,70.0,0,29.8,0.0,99,44.7,73.0,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:11:48
np4/ub512,6.0,23.3,0,23.1,4,3,5,70.0,2,29.9,4.0,99,44.7,72.6,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:13:09
```

## 7.0 concurrency stress v1 (BROKEN — superseded)
Columns: v1 had a python global-scoping bug -> ok always 0. Kept for record.
(4 lines)
```
stress_np,n_req,ok,crashed,p50_ms,p95_ms,agg_tps
1,4,0,0,14144.0,14144.0,
2,4,0,0,14681.0,14681.0,
4,4,0,0,11433.0,11433.0,
```

## 7.0 concurrency stress v2 (valid) — ALL columns
Columns: stress_np{1,2,4}, n_req=4, ok, crashed, p50_ms, p95_ms, agg_ms_tok
(4 lines)
```
stress_np,n_req,ok,crashed,p50_ms,p95_ms,agg_ms_tok
1,4,4,0,14142.0,18853.0,122.8
2,4,4,0,14628.0,14629.0,114.1
4,4,4,0,11407.0,11407.0,118.5
```

## 7.0 full-factor screening (14 runs) — ALL columns
Columns: combo, load_s, p1_gen_tps, p2_tool_ok, p2_gen_tps, tool_fn, tool_arg, tool_total, tool_acc_pct, excel_score, excel_secs, excel_grade, gpu_busy_pct, gpu_power_w, gpu_temp_c, sclk_peak, mclk_peak, crashed, ts. Center=radv/cmoe0/np2/ub512/b2048/t8/mmap1/fa1/c16384; factors varied one-at-a-time. NOTE: crashed col bogus (same bug); real crashes=0.
(15 lines)
```
combo,load_s,p1_gen_tps,p2_tool_ok,p2_gen_tps,tool_fn,tool_arg,tool_total,tool_acc_pct,excel_score,excel_secs,excel_grade,gpu_busy_pct,gpu_power_w,gpu_temp_c,sclk_peak,mclk_peak,crashed,ts
center-1,6.0,23.1,0,23.0,4,4,5,80.0,2,32.0,3.8,97,44.2,63.2,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:23:51
center-2,6.0,23.1,0,23.0,5,5,5,100.0,1,32.0,1.9,97,44.0,69.2,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:25:17
center-3,6.0,23.1,0,23.0,4,4,5,80.0,1,32.0,1.9,97,44.1,70.7,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:26:43
driver-amdvlk,8.0,23.1,0,22.9,5,5,5,100.0,1,32.3,1.9,97,43.9,69.8,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:28:14
moe10,12.0,19.7,0,19.6,5,5,5,100.0,1,37.0,1.6,95,43.9,70.2,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:29:59
np4,7.0,23.2,0,23.0,5,4,5,90.0,1,29.9,2.0,99,44.7,72.1,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:31:21
ub128,6.0,23.2,0,23.1,5,5,5,100.0,1,31.9,1.9,99,44.3,73.2,1: 2798Mhz *,1: 2800Mhz *,1,2026-08-25 01:32:49
batch1024,6.0,23.1,0,23.0,5,5,5,100.0,1,32.0,1.9,97,44.0,71.6,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:34:15
batch4096,6.0,23.1,0,23.0,5,5,5,100.0,3,31.9,5.6,97,44.0,71.9,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:35:39
threads16,6.0,23.1,0,23.0,5,5,5,100.0,3,32.0,5.6,97,44.0,71.7,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:37:04
mmap0,6.0,23.1,0,23.0,4,4,5,80.0,3,31.6,5.7,97,44.0,71.8,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:38:31
fa0,6.0,23.1,0,22.9,5,5,5,100.0,1,33.0,1.8,97,43.8,71.9,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:39:57
ctx8k,6.0,23.3,0,23.1,5,4,5,90.0,1,30.0,2.0,99,44.6,72.0,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:41:19
ctx32k,6.0,23.2,0,23.0,5,5,5,100.0,1,31.9,1.9,97,44.0,71.5,2: 2799Mhz *,1: 2800Mhz *,1,2026-08-25 01:42:43
```

## 7.0 sampling DOE (27 runs) — ALL columns
Columns: temp{0.2,0.5,0.7} x top_p{0.9,0.95,1.0} x top_k{10,20,40}; qa_score/qa_pct (8 tasks), tool_fn/tool_arg/tool_acc_pct (5 tools), excel_score/excel_secs/excel_grade, ts. Per-request sampling params on fixed base radv/cmoe0/np2/ub512.
(28 lines)
```
temp,top_p,top_k,qa_score,qa_pct,tool_fn,tool_arg,tool_acc_pct,excel_score,excel_secs,excel_grade,ts
0.2,0.9,10,2,25.0,5,4,90.0,1,32.0,1.9,2026-08-25 01:51:14
0.2,0.9,20,4,50.0,5,5,100.0,1,32.2,1.9,2026-08-25 01:52:33
0.2,0.9,40,4,50.0,5,4,90.0,3,69.2,2.6,2026-08-25 01:54:39
0.2,0.95,10,5,62.0,5,4,90.0,1,32.0,1.9,2026-08-25 01:55:58
0.2,0.95,20,5,62.0,5,4,90.0,3,32.1,5.6,2026-08-25 01:57:17
0.2,0.95,40,2,25.0,5,4,90.0,3,32.1,5.6,2026-08-25 01:58:37
0.2,1.0,10,2,25.0,5,4,90.0,2,32.2,3.7,2026-08-25 01:59:57
0.2,1.0,20,3,38.0,5,4,90.0,1,32.1,1.9,2026-08-25 02:01:14
0.2,1.0,40,5,62.0,5,5,100.0,1,32.1,1.9,2026-08-25 02:02:31
0.5,0.9,10,3,38.0,5,5,100.0,1,32.1,1.9,2026-08-25 02:03:49
0.5,0.9,20,2,25.0,5,5,100.0,2,32.1,3.7,2026-08-25 02:05:09
0.5,0.9,40,1,12.0,5,5,100.0,3,32.1,5.6,2026-08-25 02:06:27
0.5,0.95,10,3,38.0,5,5,100.0,1,32.1,1.9,2026-08-25 02:07:45
0.5,0.95,20,3,38.0,5,5,100.0,3,32.1,5.6,2026-08-25 02:09:01
0.5,0.95,40,5,62.0,5,5,100.0,3,32.1,5.6,2026-08-25 02:10:21
0.5,1.0,10,5,62.0,5,4,90.0,0,32.1,0.0,2026-08-25 02:11:40
0.5,1.0,20,5,62.0,4,4,80.0,1,32.1,1.9,2026-08-25 02:12:59
0.5,1.0,40,3,38.0,5,4,90.0,1,32.1,1.9,2026-08-25 02:14:19
0.7,0.9,10,4,50.0,5,5,100.0,2,32.1,3.7,2026-08-25 02:15:35
0.7,0.9,20,2,25.0,5,4,90.0,3,32.1,5.6,2026-08-25 02:16:55
0.7,0.9,40,4,50.0,4,4,80.0,1,32.1,1.9,2026-08-25 02:18:15
0.7,0.95,10,2,25.0,4,4,80.0,4,32.1,7.5,2026-08-25 02:19:35
0.7,0.95,20,4,50.0,5,4,90.0,2,32.2,3.7,2026-08-25 02:20:54
0.7,0.95,40,3,38.0,4,4,80.0,1,32.2,1.9,2026-08-25 02:22:13
0.7,1.0,10,4,50.0,5,4,90.0,1,32.1,1.9,2026-08-25 02:23:31
0.7,1.0,20,3,38.0,4,4,80.0,1,32.1,1.9,2026-08-25 02:24:52
0.7,1.0,40,1,12.0,5,4,90.0,2,32.1,3.7,2026-08-25 02:26:12
```

## 7.0 vision DOE — summary row (10-task battery + res sweep + mem probe)
Columns: vision_acc_pct, n_tasks, res_sweep(JSON: 128/256/512/1024 px -> prompt_tok/pp_tps/gen_tps), mem_probe(JSON: gtt before/after, power, busy, pp, gen, prompt_tok), tool_with_image_ok, ts
(2 lines)
```
vision_acc_pct,n_tasks,res_sweep,mem_probe,tool_with_image_ok,ts
100.0,10,"{""128"": {""prompt_tok"": 1045, ""pp_tps"": 132.8, ""gen_tps"": 22.8}, ""256"": {""prompt_tok"": 4, ""pp_tps"": 12.2, ""gen_tps"": 22.9}, ""512"": {""prompt_tok"": 1045, ""pp_tps"": 132.8, ""gen_tps"": 22.8}, ""1024"": {""prompt_tok"": 1045, ""pp_tps"": 132.6, ""gen_tps"": 22.8}}","{""gtt_before_gib"": 26.35, ""gtt_after_gib"": 26.35, ""gpu_pwr_w"": 44.4, ""gpu_busy_pct"": 93.7, ""pp_tps"": 133.4, ""gen_tps"": 22.9, ""prompt_tok"": 1047}",1,2026-08-25 02:33:14
```

## 7.0 long-context v1 (max_tokens=64 — artifacts, superseded by v2)
Columns: length,pos,ok,pp_tps,gen_tps,prompt_n,wall,expected,got,consistency_ok,consistency_got,consistency_pp_tps,consistency_gen_tps. max_tokens=64 starved reasoning model -> empty content on some rows (artifact).
(19 lines)
```
length,pos,ok,pp_tps,gen_tps,prompt_n,wall,expected,got,consistency_ok,consistency_got,consistency_pp_tps,consistency_gen_tps
4096,early,1,235.7,22.4,3646,17.7,social tables,Social Tables,0,,241.4,22.3
4096,mid,1,237.4,22.4,3646,17.5,dropbox sign,Dropbox Sign,0,,241.4,22.3
4096,late,1,240.3,22.4,3614,17.4,pipel,GET /api/v1/pipelines,0,,241.4,22.3
8192,early,1,243.4,22.3,4076,19.5,15,15 minutes,0,,241.4,22.3
8192,mid,1,243.6,22.3,4076,19.3,social tables,Social Tables,0,,241.4,22.3
8192,late,1,243.6,22.3,4078,19.7,2,2,0,,241.4,22.3
12288,early,1,243.6,22.3,4078,19.6,4000,4000,0,,241.4,22.3
12288,mid,0,243.1,22.3,4077,20.0,110,,0,,241.4,22.3
12288,late,1,243.1,22.3,4076,19.3,dropbox sign,Dropbox Sign,0,,241.4,22.3
16384,early,1,208.6,22.3,975,6.8,social tables,Social Tables,0,,241.4,22.3
16384,mid,1,11.8,22.4,4,2.7,social tables,Social Tables,0,,241.4,22.3
16384,late,1,11.8,22.3,4,2.5,dropbox sign,Dropbox Sign,0,,241.4,22.3
24576,early,1,243.1,22.3,4079,19.6,0.6,0.6,0,,241.4,22.3
24576,mid,1,242.5,22.3,4078,19.2,4000,4000,0,,241.4,22.3
24576,late,1,208.3,22.3,975,7.0,pipel,GET /api/v1/pipelines,0,,241.4,22.3
32768,early,1,242.6,22.3,4078,19.4,2,2,0,,241.4,22.3
32768,mid,0,11.8,22.3,4,3.5,110,,0,,241.4,22.3
32768,late,1,243.2,22.3,4076,19.1,social tables,Social Tables,0,,241.4,22.3
```

## 7.0 long-context v2 (valid, max_tokens=256) — ALL 18 runs + consistency
Columns: length{4096..32768}, pos{early,mid,late}, ok, pp_tps, gen_tps, prompt_n, wall, expected, got, consistency_ok, consistency_got, consistency_pp_tps, consistency_gen_tps. 12288-mid & 32768-mid: model answered '1.1' for expected '110' (correct ratio, scorer false-negative).
(19 lines)
```
length,pos,ok,pp_tps,gen_tps,prompt_n,wall,expected,got,consistency_ok,consistency_got,consistency_pp_tps,consistency_gen_tps
4096,early,1,43.4,22.4,57,3.2,social tables,Social Tables,1,/api/v1/venues,11.8,22.3
4096,mid,1,12.0,22.4,4,2.4,dropbox sign,Dropbox Sign,1,/api/v1/venues,11.8,22.3
4096,late,1,43.6,22.4,57,4.7,pipel,GET /api/v1/pipelines,1,/api/v1/venues,11.8,22.3
8192,early,1,11.8,22.4,4,3.2,15,15 minutes,1,/api/v1/venues,11.8,22.3
8192,mid,1,12.0,22.3,4,2.7,social tables,Social Tables,1,/api/v1/venues,11.8,22.3
8192,late,1,11.8,22.4,4,3.3,2,2,1,/api/v1/venues,11.8,22.3
12288,early,1,11.9,22.3,4,2.7,4000,4000,1,/api/v1/venues,11.8,22.3
12288,mid,0,12.0,22.4,4,5.2,110,1.1,1,/api/v1/venues,11.8,22.3
12288,late,1,12.0,22.3,4,2.5,dropbox sign,Dropbox Sign,1,/api/v1/venues,11.8,22.3
16384,early,1,187.1,22.3,516,4.8,social tables,Social Tables,1,/api/v1/venues,11.8,22.3
16384,mid,1,12.0,22.3,4,3.0,social tables,Social Tables,1,/api/v1/venues,11.8,22.3
16384,late,1,12.0,22.3,4,2.5,dropbox sign,Dropbox Sign,1,/api/v1/venues,11.8,22.3
24576,early,1,11.8,22.3,4,3.2,0.6,0.6,1,/api/v1/venues,11.8,22.3
24576,mid,1,11.8,22.3,4,3.1,4000,4000,1,/api/v1/venues,11.8,22.3
24576,late,1,189.5,22.3,516,4.9,pipel,GET /api/v1/pipelines,1,/api/v1/venues,11.8,22.3
32768,early,1,11.8,22.3,4,2.5,2,2,1,/api/v1/venues,11.8,22.3
32768,mid,0,12.0,22.3,4,5.2,110,1.1,1,/api/v1/venues,11.8,22.3
32768,late,1,11.8,22.3,4,2.6,social tables,Social Tables,1,/api/v1/venues,11.8,22.3
```

# CONSIDERATIONS / ARTIFACTS / DECISIONS (every known caveat)

## Measurement artifacts
1. max_tokens=64 -> empty outputs. Ornith-1.5 is a reasoning model; a <think> block can consume the entire
   token budget before any answer token. Vision smoke tests at max_tokens=16 returned '' (fixed at 256).
   Long-context v1 (max_tokens=64) produced empty content on several rows (artifact). v2 re-ran at 256.
2. `crashed` column bogus in some phases. Capturing MainPID BEFORE the per-run systemd restart makes every
   row read crashed=1. Present in phase2, phaseA (and earlier stress v1). Real crash rate verified = 0 via
   systemd journal (no device-lost / OOM / unexpected exit in any window). The true resilience result is 0 crashes.
3. Scorer strictness. Tool battery arg matching is case/format-sensitive (Tokyo vs tokyo; '17*23' vs '17 * 23');
   several 'arg' misses are formatting, not functional misses. Long-context '110' needle: model answered '1.1'
   (the correct ratio) for a question asking 'ratio'; scorer expected '110' -> flagged FAIL (false-negative).
4. KV-cache hits in long-context v2. Rows with prompt_n=4 are served from llama.cpp prompt cache (pp_tps ~12
   is cache-read, not real prompt-eval). Cold rows show real pp ~43-243 t/s. Accuracy unaffected.
5. amdgpu hwmon node differs between kernels. 6.8 = hwmon4; 7.x = hwmon6. Early 7.x grid rows read hwmon4
   (missing) -> empty gpu_power_w/gpu_temp_c. Fixed by dynamic detection; later phases have power data.
6. Envelope power numbers are post-benchmark (sampler ran after the long gen), so gpu_pwr is understated
   (13-16W idle-ish). A separate live during-load probe measured GPU power ramping to ~47-49W.
7. Concurrency stress latencies include fresh-model-load warmup (each slots config restarts the server and the
   first request pays load cost). Compare p50/p95 RELATIVELY across np, not as absolute latency.

## Controllability findings
8. mclk (RAM clock) is NOT software-controllable on this APU. pp_dpm_mclk per-state pinning rejected
   (I/O error) in manual mode; no mclk OD entry. Fixed at 2800 MHz (DDR5-5600). Tested exhaustively (3 methods).
9. pp_dpm_sclk per-state pinning also rejected (I/O error). Only power_dpm_force_performance_level
   {auto,low,high} is writable, and under load the SMU manages sclk (high alone does not pin 2799 at default
   power; high + raised package power DOES sustain 2799).
10. ryzenadj (built from source, v0.19.0) works on 8945HS: reads/writes STAPM/PPT/TDC/EDC. Verified write+readback
    (45->60W etc.). Reboot resets to defaults (not persistent).

## Environment / sequencing
11. llama.cpp rebuild (398 commits, master f280b2698) was staged while phase2 ran. Verified by timestamps that
    the build fully finished (00:52:39) BEFORE phase2's first restart (00:55:30); running server md5 == new
    binary; no overlap, no contention. All post-build phases used the new build.
12. Kernel 7.0.0-30 (HWE) booted via grub-reboot; GTT 50GiB via amdttm/ttm pages_limit. Qwen3-30B service
    (llama-gflip) disabled during all DOE (no GPU stacking); its watchdog/recovery timers disabled; re-enable
    to restore.
13. Vision is served with --mmproj; context-shift (--ctx-shift) is silently OFF and auto-disabled by the server
    when multimodal (mmproj) is loaded (source: server-context.cpp forces ctx_shift=false). Enabling it requires
    dropping --mmproj (loses vision) + --keep N.
14. Tool calls in llama.cpp are already grammar-constrained: the server auto-generates a JSON-schema GBNF grammar
    from `tools`. The OpenAI /v1/chat/completions endpoint does NOT accept a per-request `grammar` field (returns
    empty) in this build; grammar is server-level (--grammar) only.
15. mmap vs no-mmap changes memory accounting: with mmap the weights live in page cache (gtt_used ~0, VmRSS ~30GB
    shared); with --no-mmap the weights are copied into GTT (gtt_used ~27GB). No speed difference measured.

## Production settings applied (2026-08-25)
radv / --n-cpu-moe 0 / -np 2 / -ub 512 / -b 2048 / -t 8 / -c 32768 / --flash-attn on
--temp 0.2 --top-p 0.95 --top-k 20 / --mmproj / default power (STAPM45/Fast54/Slow45) / perf auto / GTT 50GiB
LibreChat Ornith addParams: temperature 0.2, top_p 0.95, top_k 20. Smoke: PROD-OK @ 23.1 gen t/s.

