"""Validated, versioned cloud contracts and privacy-safe public representations."""
import math
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

POLICY_VERSION = 'school-planning-2026-10-v1'
ROLES = ('parent', 'teacher', 'staff', 'admin', 'kid')
CHANNELS = ('in-app', 'push', 'email', 'sms', 'whatsapp')
DEFAULT_PREFS = {'language': 'en', 'channels': ['in-app'], 'quietStart': '21:00',
                 'quietEnd': '06:00', 'dailyCap': 4, 'morning': True}


class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def text(value, name, maximum=100, minimum=1):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise Problem(f'{name} must contain {minimum}–{maximum} characters.')
    return value.strip()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise Problem('Invalid identifier.')
    return value


def number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise Problem(f'{name} must be between {low} and {high}.')
    return value


def integer(value, name, low, high):
    number(value, name, low, high)
    if not isinstance(value, int):
        raise Problem(f'{name} must be a whole number.')
    return value


def clock(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
        raise Problem('Use a valid HH:MM time.')
    return value


def school(data):
    from cloud.dayplan import validate_blocks, DEFAULT_BLOCKS
    zone = data.get('timezone', 'Asia/Kolkata')
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        raise Problem('Choose a valid IANA timezone.')
    building = data.get('building_type', 'unknown')
    if building not in ('ac', 'non-ac', 'mixed', 'unknown'):
        raise Problem('Choose AC, non-AC, mixed or unknown building type.')
    return {'id': identifier(data['id']), 'name': text(data.get('name'), 'School name'),
            'lat': number(data.get('lat'), 'Latitude', -90, 90),
            'lon': number(data.get('lon'), 'Longitude', -180, 180), 'timezone': zone,
            'building_type': building, 'ventilation': text(data.get('ventilation', 'unknown'), 'Ventilation', 200),
            'filtration': text(data.get('filtration', 'unknown'), 'Filtration', 200),
            'cpcb_city': text(data.get('cpcb_city') or 'unconfigured', 'CPCB city', 100),
            'outdoor_area_score': number(data.get('outdoor_area_score', 0), 'Outdoor area score', 0, 5),
            'outdoor_area_notes': text(data.get('outdoor_area_notes', 'Not assessed'), 'Outdoor area notes', 300),
            'school_start': clock(data.get('school_start', '08:00')), 'school_end': clock(data.get('school_end', '15:00')),
            'timetable': validate_blocks(data.get('timetable', DEFAULT_BLOCKS)),
            'policyVersion': POLICY_VERSION, 'active': True}


def preferences(data):
    if data.get('language') not in ('en', 'hi', 'mr'):
        raise Problem('Choose English, Hindi or Marathi.')
    channels = data.get('channels')
    if not isinstance(channels, list) or not channels or any(c not in CHANNELS for c in channels):
        raise Problem('Choose supported notification channels.')
    if not isinstance(data.get('morning'), bool):
        raise Problem('Morning preference must be true or false.')
    return {'language': data['language'], 'channels': sorted(set(channels)),
            'quietStart': clock(data.get('quietStart')), 'quietEnd': clock(data.get('quietEnd')),
            'dailyCap': integer(data.get('dailyCap'), 'Daily cap', 1, 10), 'morning': data['morning']}


def local_day(config, now=None):
    return datetime.fromtimestamp(time.time() if now is None else now, ZoneInfo(config['timezone'])).date().isoformat()


def quiet(prefs, config, now):
    current = datetime.fromtimestamp(now, ZoneInfo(config['timezone'])).strftime('%H:%M')
    start, end = prefs['quietStart'], prefs['quietEnd']
    return start <= current < end if start < end else current >= start or current < end if start != end else False
