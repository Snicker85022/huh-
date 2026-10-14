"""Distributed vision voting coordinator.

Nodes register and vote on detection tasks (e.g., 'find chrome pole x positions').
gflip local nodes: SAM, YOLOv8n-ONNX, LLaVA-7B, Llama3.2-Vision-11B.
MicroTouch nodes: to be added once ADB is authorized (ONNX/NNAPI models planned).
"""
import json, os, sqlite3, datetime, threading, subprocess, base64, urllib.request

DB = os.path.expanduser('~/vision-stack/world/world.db')
VOTES_FILE = '/tmp/vision_votes.json'

NODES = {
    'gflip_sam': {'host': 'local', 'type': 'segmentation', 'status': 'ready'},
    'gflip_yolov8n': {'host': 'local', 'type': 'detection', 'status': 'ready'},
    'gflip_llava7b': {'host': 'local', 'type': 'vlm', 'status': 'ready'},
    'gflip_llama3.2_vision': {'host': 'local', 'type': 'vlm', 'status': 'ready'},
    'mt1_onnx': {'host': '192.168.2.104', 'type': 'npu', 'status': 'ADB_UNAUTHORIZED'},
    'mt2_onnx': {'host': '192.168.2.108', 'type': 'npu', 'status': 'ADB_UNAUTHORIZED'},
}

def status():
    return NODES

def vote(task, votes):
    """votes: list of {node, answer, confidence}. Majority/weighted vote."""
    if not votes:
        return {'decision': None, 'reason': 'no votes'}
    # weighted average by confidence for numeric answers
    numerics = [v for v in votes if isinstance(v.get('answer'), (int, float))]
    if numerics:
        total_w = sum(v['confidence'] for v in numerics)
        decision = sum(v['answer']*v['confidence'] for v in numerics)/total_w
        return {'decision': decision, 'votes': votes, 'weighted': True}
    return {'decision': votes[0]['answer'], 'votes': votes, 'weighted': False}
