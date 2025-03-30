#!/usr/bin/env python3
# coding: utf-8

from flask import Flask, request, jsonify
import smbus
from time import sleep
from queue import Queue
from threading import Thread

app = Flask(__name__)

# I2C設定
bus = smbus.SMBus(1)
SLAVE_ADDRESS = 0x5A
R1_log_start = 0x15
R2_log_stop = 0x25
R3_data_num_read = 0x35
R4_data_read = 0x45
W1_data_num_write = 0x19
W2_data_write = 0x29
W3_trans_req = 0x39

send_queue = Queue()

def read_command():
    bus.write_byte(SLAVE_ADDRESS, R1_log_start)
    sleep(5.0)
    bus.write_byte(SLAVE_ADDRESS, R2_log_stop)
    data_numHL = bus.read_i2c_block_data(SLAVE_ADDRESS, R3_data_num_read, 3)
    data_num = data_numHL[1] * 256 + data_numHL[2]
    if data_num >= 65535:
        return None
    bus.read_i2c_block_data(SLAVE_ADDRESS, R4_data_read, 1)
    block = []
    for _ in range(data_num):
        block.extend(bus.read_i2c_block_data(SLAVE_ADDRESS, R4_data_read, 4))
    return block

def write_command(block2):
    int_tmp = [int(block2[i*2:(i*2+2)], 16) for i in range(len(block2)//2)]
    data_num = len(int_tmp) // 4
    bus.write_i2c_block_data(SLAVE_ADDRESS, W1_data_num_write, [data_num >> 8, data_num & 0xFF])
    for i in range(data_num):
        bus.write_i2c_block_data(SLAVE_ADDRESS, W2_data_write, int_tmp[i*4:(i+1)*4])
    bus.write_byte(SLAVE_ADDRESS, W3_trans_req)
    return True

def worker():
    while True:
        hex_data = send_queue.get()
        try:
            write_command(hex_data)
            sleep(0.5)
        except Exception as e:
            app.logger.error(f"IR送信失敗: {e}")
        finally:
            send_queue.task_done()

Thread(target=worker, daemon=True).start()

@app.route('/read', methods=['GET'])
def api_read():
    try:
        block = read_command()
        if block is None:
            return jsonify({'error': 'data_num error'}), 500
        return jsonify({'data': ''.join(f"{b:02X}" for b in block)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/write', methods=['POST'])
def api_write():
    data = request.get_json() or {}
    hex_data = data.get('data')
    if not hex_data:
        return jsonify({'error': 'data is required'}), 400
    send_queue.put(hex_data)
    return jsonify({'status': 'queued'}), 202

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
