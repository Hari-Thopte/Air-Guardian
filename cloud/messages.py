"""Server messages use the same action-code catalogue as the browser."""
from cloud.catalogue import phrase, action_message


def role_message(event, role, language='en'):
    flag=event['flag']
    code='rotate' if flag=='red' and role=='staff' else 'indoor-pe' if flag in ('red','orange') else 'gentle' if flag=='yellow' else 'usual' if flag=='green' else 'verify'
    return f"{phrase('notification.prefix',language)}: {phrase('flag.'+flag,language).upper()}. {action_message(code,language)}"
