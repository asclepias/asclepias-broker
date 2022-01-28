
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Monitoring tasks"""

import datetime

from sqlalchemy.orm.util import join
from celery import  shared_task
from sqlalchemy import and_
from invenio_db import db
import slack
import os

from ..monitoring.models import ErrorMonitoring, HarvestMonitoring, HarvestStatus
from ..events.models import Event, EventStatus
from ..events.api import EventAPI
from ..harvester.cli import rerun_event

@shared_task(ignore_result=True)
def rerun_harvest_errors():
    two_days_ago = datetime.datetime.now() - datetime.timedelta(days = 2)
    resp = HarvestMonitoring.query.filter(HarvestMonitoring.status == HarvestStatus.Error, HarvestMonitoring.created > str(two_days_ago)).all()
    for event in resp:
        rerun_event(event, no_index=True, eager=False)

@shared_task(ignore_result=True)
def rerun_event_errors():
    two_days_ago = datetime.datetime.now() - datetime.timedelta(days = 2)
    resp = Event.query.filter(Event.status == EventStatus.Error, Event.created > str(two_days_ago)).all()
    for event in resp:
        EventAPI.rerun_event(event, no_index=True, eager=False)

@shared_task(ignore_result=True)
def sendMonitoringReport():
    """Sends monitor report to the Slack bot defined with SLACK_API_TOKEN in the enviroment
    
    Sends a report of the number of events and harvester that have been done during the last 7 days 
    and also adds a list of all errors that have taken place during the ingestions"""

    slack_token = os.environ.get("SLACK_API_TOKEN")
    if slack_token is not None and slack_token != "CHANGE_ME":
        client = slack.WebClient(token=slack_token)
        channel = 'broker-alerts'
        sendHarvestErrors(client, channel)
        sendEventErrors(client, channel)
        sendHarvestReport(client, channel)
        sendEventReport(client, channel)

def sendHarvestErrors(client, channel):
    errors = (db.session.query(ErrorMonitoring)
    .join(HarvestMonitoring, ErrorMonitoring.event_id == HarvestMonitoring.id)
    .filter(HarvestMonitoring.status == HarvestStatus.Error))
    sendErrorReport(errors, client, channel)

def sendEventErrors(client, channel):
    errors = (db.session.query(ErrorMonitoring)
    .join(Event, ErrorMonitoring.event_id == Event.id)
    .filter(Event.status == EventStatus.Error))
    sendErrorReport(errors, client, channel)

def sendErrorReport(errors, client, channel:str):
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