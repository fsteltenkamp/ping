#!/bin/env python3
#imports
import argparse
import re
import shutil
import statistics
import subprocess
import simplejson
import json
import time
import os
import yaml
import logging
import requests
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

def getPoints(fpingOl, pingCount, start_timestamp, src_host_name):
    points = []
    for line in fpingOl:
        host = re.split(' +: +', line)[0]
        responses = re.split(' +: +', line)[1].split(' ')
        pings = [float(response) for response in responses if response !='-']
        pingsNoStr = []
        for ping in pings:
            if ping != '-':
                pingsNoStr.append(ping)
        logging.debug('processing results for ' + host + '.')

        if len(pings) == 0:
            logging.warning('100% Loss for ' + host)
            average = float(0)
            psdeviation = float(0)
            loss = round(responses.count('-') / pingCount, 2)
            minRes = float(0)
            maxRes = float(0)
        else:
            #collect data:
            average = float(round(statistics.mean(pings), 2))
            psdeviation = float(round(statistics.pstdev(pings), 2))
            loss = float(round(responses.count("-") / pingCount, 2))
            minRes = float(round(min(pingsNoStr)))
            maxRes = float(round(max(pingsNoStr)))

        points.append({
            "time": time.strftime('%Y-%m-%dT%H:%M:%SZ', start_timestamp),
            "measurement": "ping",
            "tags": {
                "src": src_host_name,
                "dest": host,
            },
            "fields": {
                "avg": average,
                "sd": psdeviation,
                "loss": loss,
                "min": minRes,
                "max": maxRes,
            }
        })
    logging.debug(points)
    return points

def postToInfluxDb(points):
    client = InfluxDBClient(
        url=str(os.environ.get('INFLUXDB_URL')),
        token=str(os.environ.get('INFLUXDB_TOKEN')),
        org=str(os.environ.get('INFLUXDB_ORG'))
    )
    writeClient = client.write_api(
        write_options=WriteOptions(
            batch_size=500,
            flush_interval=10_000,
            jitter_interval=2_000,
            retry_interval=5_000,
            max_retries=5,
            max_retry_delay=30_000,
            exponential_base=2
        )
    )
    writeClient.write(
        bucket=str(os.environ.get('INFLUXDB_BUCKET')),
        org=str(os.environ.get('INFLUXDB_ORG')),
        record=points
    )
    writeClient.__del__()
    client.__del__()

def getDevicesFromApi(url, api_token):
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_token}
    # pull:
    if os.environ.get('API_SSL_VERIFY') and os.environ.get('API_SSL_VERIFY') == 'false':
        r = requests.get(url, headers=headers, verify=False)
    else:
        r = requests.get(url, headers=headers)
    devicesJson = r.text
    # parse json:
    devices = json.loads(devicesJson)
    return devices

def getDevices():
    hosts = []
    devices = []
    if os.environ.get('URL') and os.environ.get('API_TOKEN'):
        logging.info('Requesting hosts from API.')
        url = os.environ.get('URL')
        api_token = os.environ.get('API_TOKEN')
        devices = getDevicesFromApi(url, api_token)
        devices = devices['devices']
        for device in devices:
            ip = device['publicIp']
            hosts.append(ip)
    elif os.environ.get('TARGETS_FILE'):
        logging.info('Using hosts from provided file.')
        hostsFile = os.environ.get('HOSTS_FILE')
        with open(hostsFile, "r") as f:
            devices = simplejson.load(f)
            devices = devices['devices']
            for device in devices:
                ip = device['publicIp']
                hosts.append(ip)
    elif os.environ.get('HOST_LIST'):
        logging.info('Using provided hosts.')
        devices = os.environ.get('HOST_LIST')
        hosts = devices.split(',')
    else:
        logging.error('No hosts provided. Exiting.')
        exit(1)
    #debug:
    logging.debug('hosts:')
    logging.debug(hosts)
    concatenatedHosts = '\n'.join(hosts)
    return concatenatedHosts

# config:
basedir = "/ping_script"
datadir = "/ping"

# Logging Config:
loggingHandler = logging.StreamHandler()
loggingHandler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s'))
if os.environ.get('DEBUG') == 'true':
    logging.getLogger().setLevel(logging.DEBUG)
else:
    logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(loggingHandler)

#main:
logging.info('Starting ping script.')
if os.environ.get('BOOT_DELAY') and int(os.environ.get('BOOT_DELAY')) > 0:
    logging.info('Waiting for ' + os.environ.get('BOOT_DELAY') + ' seconds to allow for other services to start.')
    time.sleep(int(os.environ.get('BOOT_DELAY')))
logging.info('Starting main loop.')
while 1:
    pingCount = int(os.environ.get('PING_COUNT'))
    sleepTime = int(os.environ.get('INTERVAL'))
    hostName = os.environ.get('SRC_HOST_NAME') or 'localhost'
    concatenatedHosts = getDevices()
    start_timestamp = time.gmtime()
    logging.info('starting new session @' + time.strftime('%Y%m%d-%H:%M:%SZ', start_timestamp))
    fping_run = subprocess.run([shutil.which('fping'), '-C', str(pingCount), '-q', '-R'], input=concatenatedHosts, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    fping_output_lines = fping_run.stdout.splitlines()
    logging.debug('fping_output_lines:')
    logging.debug(fping_output_lines)
    points = getPoints(fping_output_lines, pingCount, start_timestamp, hostName)
    if os.environ.get('INFLUXDB_URL') and os.environ.get('INFLUXDB_ORG') and os.environ.get('INFLUXDB_TOKEN') and os.environ.get('INFLUXDB_BUCKET'):
        postToInfluxDb(points)
    else:
        logging.error('No InfluxDB credentials provided. Dumping results to stdout.')
        logging.debug('URL: ' + os.environ.get('INFLUXDB_URL'))
        logging.debug('ORG: ' + os.environ.get('INFLUXDB_ORG'))
        logging.debug('TOKEN: ' + os.environ.get('INFLUXDB_TOKEN'))
        logging.debug('BUCKET: ' + os.environ.get('INFLUXDB_BUCKET'))
        logging.error(points)
    end_timestamp = time.gmtime()
    logging.info('finished session @' + time.strftime('%Y%m%d-%H:%M:%SZ', end_timestamp))
    logging.info('sleeping for ' + str(sleepTime) + ' seconds.')
    time.sleep(sleepTime)
