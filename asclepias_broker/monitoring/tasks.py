
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
def sendMonitoringReport():
    slack_token = os.environ.get("SLACK_API_TOKEN")
    if slack_token is not None and slack_token != "CHANGE_ME":
        client = slack.WebClient(token=slack_token)
        channel = 'broker-alerts'
        sendErrorReport(client, channel)
        sendHarvestReport(client, channel)
        sendEventReport(client, channel)

def sendErrorReport(client, channel:str):
    errors = ErrorMonitoring.getLastWeeksErrors()
    blocks = []
    blocks.append({"type": "section",
                "text": {
                    "text": "*Errors during the last 7 days*",
                    "type": "mrkdwn"
                },
        })
    for i, error in enumerate(errors):
        err_dict = error.to_dict()
        fields = [{
            "type": "plain_text",
            "text": 'origin'
        },
        {
            "type": "plain_text",
            "text": str(err_dict['origin'])
        },
        {
            "type": "plain_text",
            "text": 'created'
        },{
            "type": "plain_text",
            "text": str(err_dict['created'])
        },{
            "type": "plain_text",
            "text": 'error'
        },{
            "type": "plain_text",
            "text": str(err_dict['error']).replace('\\n', '\n')
        },{
            "type": "plain_text",
            "text": 'payload'
        },{
            "type": "plain_text",
            "text": str(err_dict['payload']).replace('\\n', '\n')
        }]
        blocks.append({"type": "section",
                "text": {
                    "text": "Error #" + str(i),
                    "type": "mrkdwn"
                },
                "fields":fields
        })

        if i % 40 == 0:
            client.chat_postMessage(channel=channel, blocks=blocks)
            blocks = []
    if len(blocks) > 0:
        client.chat_postMessage(channel=channel, blocks=blocks)


def sendHarvestReport(client, channel:str):
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
    if len(fields) == 0:
         fields.append({
            "type": "plain_text",
            "text": "Done"
        })
         fields.append({
            "type": "plain_text",
            "text": str(0)
        })
    blocks = [{"type": "section",
        "text": {
            "text": "*Number of harvests done during the last 7 days*",
            "type": "mrkdwn"
        },
        "fields":fields
    }]
    client.chat_postMessage(channel=channel, blocks=blocks)


def sendEventReport(client, channel:str):
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
    if len(fields) == 0:
         fields.append({
            "type": "plain_text",
            "text": "Done"
        })
         fields.append({
            "type": "plain_text",
            "text": str(0)
        })
    blocks = [{"type": "section",
        "text": {
            "text": "*Number of events done during the last 7 days*",
            "type": "mrkdwn"
        },
        "fields":fields
    }]
    client.chat_postMessage(channel=channel, blocks=blocks)