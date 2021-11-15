
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
    errors = ErrorMonitoring.getLastWeeksErrors()
    blocks = []
    blocks.append({"type": "section",
                "text": {
                    "text": "*Errors during the last 7 days*",
                    "type": "mrkdwn"
                },
        })
    for i, error in enumerate(errors):
        fields = [{
            "type": "plain_text",
            "text": 'origin'
        },
        {
            "type": "plain_text",
            "text": str(error['origin'])
        },
        {
            "type": "plain_text",
            "text": 'created'
        },{
            "type": "plain_text",
            "text": str(error['created'])
        },{
            "type": "plain_text",
            "text": 'error'
        },{
            "type": "plain_text",
            "text": str(error['error']).replace('\\n', '\n')
        }]
        blocks.append({"type": "section",
                "text": {
                    "text": "Error #" + str(i),
                    "type": "mrkdwn"
                },
                "fields":fields
        })

    client.chat_postMessage(channel='test', blocks=blocks)
    # client.chat_postMessage(channel='test', text="Errors received during the last 7 days")
    # client.chat_postMessage(channel='test', text=msg)

def sendHarvestReport(client):
    list = HarvestMonitoring.getStatsFromLastWeek()
    fields = []
    for obj in list:
        fields.append({
            "type": "plain_text",
            "text": obj[0].name
        })
        fields.append({
            "type": "plain_text",
            "text": str(obj[1])
        })
    blocks = [{"type": "section",
            "text": {
                "text": "*Number of harvests done during the last 7 days*",
                "type": "mrkdwn"
            },
            "fields":fields
    }]
    client.chat_postMessage(channel='test', blocks=blocks)


def sendEventReport(client):
    list = Event.getStatsFromLastWeek()
    fields = []
    for obj in list:
        fields.append({
            "type": "plain_text",
            "text": obj[0].name
        })
        fields.append({
            "type": "plain_text",
            "text": str(obj[1])
        })
    blocks = [{"type": "section",
            "text": {
                "text": "*Number of harvests done during the last 7 days*",
                "type": "mrkdwn"
            },
            "fields":fields
    }]
    client.chat_postMessage(channel='test', blocks=blocks)