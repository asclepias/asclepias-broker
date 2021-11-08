
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Monitoring notifications"""

from ..monitoring.models import ErrorMonitoring, HarvestMonitoring
from ..events.models import Event
from celery import  shared_task
from sqlalchemy import and_
import slack
import os

@shared_task()
def test():
    slack_token = os.environ.get("SLACK_API_TOKEN")
    if slack_token is not None and slack_token != "CHANGE_ME":
        client = slack.WebClient(token=slack_token)
        sendErrorReport(client)
        sendHarvestReport(client)
        sendEventReport(client)

def sendErrorReport(client):
    error_list = ErrorMonitoring.getLastWeeksErrors()
    str_list = [repr(err) for err in error_list]
    msg = "[" + ",".join(str_list) + "]"
    client.chat_postMessage(channel='test', text="Errors received during the last 7 days")
    client.chat_postMessage(channel='test', text=msg)

def sendHarvestReport(client):
    list = HarvestMonitoring.getStatsFromLastWeek()
    str_list = [str(obj) for obj in list]
    msg = "[" + ",".join(str_list) + "]"
    client.chat_postMessage(channel='test', text="Number of harvests done during the last 7 days")
    client.chat_postMessage(channel='test', text=msg)

def sendEventReport(client):
    list = Event.getStatsFromLastWeek()
    str_list = [str(obj) for obj in list]
    msg = "[" + ",".join(str_list) + "]"
    client.chat_postMessage(channel='test', text="Number of events done during the last 7 days")
    client.chat_postMessage(channel='test', text=msg)