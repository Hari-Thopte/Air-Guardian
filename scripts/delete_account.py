"""Operator erasure with a durable restore-block ledger. Defaults to a review-only plan."""
import argparse
import time
try:
    from .aws_support import ROOT, outputs
except ImportError:
    from aws_support import ROOT, outputs
from cloud.store import DynamoStore, change
import boto3


def affected_schools(store, subject):
    # The explicit school index also finds remnants after a prior unlink.
    schools = store.query('SCHOOLS', limit=1000)
    if len(schools) >= 1000:
        raise ValueError('School index exceeds the pilot erasure bound; use a paginated operator process.')
    return [r['id'] for r in schools]


def erase_application(store, subject, schools):
    for sid in schools:
        pk = 'SCHOOL#' + sid
        who = store.get(pk, 'MEMBER#' + subject)
        if who:
            store.commit([change(pk, 'MEMBER#' + subject, None, who)])
        for child in store.query(pk, 'CHILD#', limit=1000):
            if subject in child.get('guardians', []):
                guardians = [s for s in child['guardians'] if s != subject]
                store.commit([change(pk, child['_sk'], dict(child, guardians=guardians) if guardians else None, child)])
        cleanup = store.get('ERASURE', sid + '#' + subject)
        if cleanup:
            store.commit([change('ERASURE', sid + '#' + subject, None, cleanup)])
    while True:
        rows = store.query('USER#' + subject, limit=50)
        if not rows:
            break
        store.commit([change('USER#' + subject, row['_sk'], None, row) for row in rows])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stack', default='air-guardian-pilot')
    parser.add_argument('--region', default='ap-south-1')
    parser.add_argument('--username', required=True, help='Cognito username/email')
    parser.add_argument('--subject', required=True, help='Verified Cognito sub; retained for restart recovery')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    session = boto3.Session(region_name=args.region)
    values = outputs(session, args.stack)
    boto3.setup_default_session(region_name=args.region)
    store = DynamoStore(values['AppTableName'])
    cognito = session.client('cognito-idp')
    ledger = store.get('ACCOUNT_ERASURE', args.subject)
    try:
        user = cognito.admin_get_user(UserPoolId=values['UserPoolId'], Username=args.username)
        if dict((a['Name'], a['Value']) for a in user['UserAttributes']).get('sub') != args.subject:
            raise ValueError('Username does not match subject.')
    except cognito.exceptions.UserNotFoundException:
        if not ledger:
            raise ValueError('No matching user or resumable erasure ledger.') from None
    schools = affected_schools(store, args.subject)
    for sid in schools:
        pk = 'SCHOOL#' + sid
        member = store.get(pk, 'MEMBER#' + args.subject) or {}
        if member.get('active') and member.get('role') == 'admin' and not any(
            r.get('active') and r.get('role') == 'admin' and r['sub'] != args.subject for r in store.query(pk, 'MEMBER#')):
            raise ValueError('Assign another administrator to ' + sid + ' before erasure.')
    print('Plan: disable/delete Cognito identity; erase personal partition, memberships and sole-guardian child aliases.')
    print('School operational receipts retain their existing TTL. PITR/backups require ledger replay before restoration.')
    if not args.execute:
        print('Review-only: rerun with --execute to perform this specific account erasure.')
        return
    if not ledger:
        store.commit([change('ACCOUNT_ERASURE', args.subject, {'requestedAt': time.time(), 'status': 'pending'})])
    try:
        cognito.admin_disable_user(UserPoolId=values['UserPoolId'], Username=args.username)
        cognito.admin_user_global_sign_out(UserPoolId=values['UserPoolId'], Username=args.username)
    except cognito.exceptions.UserNotFoundException:
        pass
    erase_application(store, args.subject, schools)
    try:
        cognito.admin_delete_user(UserPoolId=values['UserPoolId'], Username=args.username)
    except cognito.exceptions.UserNotFoundException:
        pass
    ledger = store.get('ACCOUNT_ERASURE', args.subject)
    store.commit([change('ACCOUNT_ERASURE', args.subject, dict(ledger, status='complete', completedAt=time.time()), ledger)])
    print('Erasure complete. Preserve the ledger and replay it before restoring a backup.')


if __name__ == '__main__':
    main()
