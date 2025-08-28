"""Module listant les privilèges des comptes du AWS Identity Center"""

import csv
import sys
from collections import defaultdict
from datetime import date
import boto3


def paginate(method, result_key, **kwargs):
    """Pagination logic"""
    token_key = "NextToken"
    while True:
        resp = method(**kwargs)
        for item in resp.get(result_key, []):
            yield item
        token = resp.get(token_key)
        if not token:
            break
        kwargs["NextToken"] = token

# ---------- Clients ----------
sso_admin = boto3.client("sso-admin")
identitystore = boto3.client("identitystore")
org = boto3.client("organizations")

# ---------- Discover instance ----------
instances = sso_admin.list_instances().get("Instances", [])
if not instances:
    print("Aucune instance IAM Identity Center trouvée pour ce compte/région.", file=sys.stderr)
    sys.exit(1)

instance = instances[0]
INSTANCE_ARN = instance["InstanceArn"]
IDENTITY_STORE_ID = instance["IdentityStoreId"]

# ---------- Accounts (Organizations) ----------
accounts = {}
for acct in paginate(org.list_accounts, "Accounts"):
    accounts[acct["Id"]] = acct.get("Name", "")

# ---------- Users ----------
users = {}
for u in paginate(identitystore.list_users, "Users", IdentityStoreId=IDENTITY_STORE_ID):
    user_id = u["UserId"]
    user_name = u.get("UserName") or ""
    display = u.get("DisplayName") or ""
    emails = u.get("Emails") or []
    EMAIL = ""
    if emails:
        prim = [e for e in emails if e.get("Primary")]
        EMAIL = (prim[0] if prim else emails[0]).get("Value", "")
    users[user_id] = {
        "UserName": user_name,
        "DisplayName": display,
        "Email": EMAIL
    }

# ---------- Groups & membership ----------
groups = {}
group_members = defaultdict(set)

for g in paginate(identitystore.list_groups, "Groups", IdentityStoreId=IDENTITY_STORE_ID):
    gid = g["GroupId"]
    gname = g.get("DisplayName") or g.get("ExternalIds", [{}])[0].get("Id", "") or gid
    groups[gid] = gname

    for gm in paginate(identitystore.list_group_memberships, "GroupMemberships",
                       IdentityStoreId=IDENTITY_STORE_ID, GroupId=gid):
        member = gm.get("MemberId", {})
        uid = member.get("UserId")
        if uid:
            group_members[gid].add(uid)

# ---------- Permission sets ----------
ps_arns = list(paginate(sso_admin.list_permission_sets, "PermissionSets", InstanceArn=INSTANCE_ARN))

ps_names = {}
for ps_arn in ps_arns:
    d = sso_admin.describe_permission_set(InstanceArn=INSTANCE_ARN, PermissionSetArn=ps_arn)
    ps_names[ps_arn] = d["PermissionSet"]["Name"]

# ---------- Collecte des attributions ----------
rows = []

for ps_arn in ps_arns:
    ps_name = ps_names[ps_arn]

    for acct_id in paginate(
        sso_admin.list_accounts_for_provisioned_permission_set,
        "AccountIds",
        InstanceArn=INSTANCE_ARN,
        PermissionSetArn=ps_arn,
        ProvisioningStatus="LATEST_PERMISSION_SET_PROVISIONED",  # <-- fix
    ):
        acct_name = accounts.get(acct_id, "")

        assignments = list(paginate(
            sso_admin.list_account_assignments,
            "AccountAssignments",
            InstanceArn=INSTANCE_ARN,
            AccountId=acct_id,
            PermissionSetArn=ps_arn
        ))

        for asg in assignments:
            principal_type = asg["PrincipalType"]  # USER | GROUP
            principal_id = asg["PrincipalId"]

            if principal_type == "USER":
                if principal_id in users:
                    uinfo = users[principal_id]
                    rows.append([
                        uinfo["UserName"],
                        principal_id,
                        uinfo["DisplayName"],
                        uinfo["Email"],
                        acct_id,
                        acct_name,
                        ps_name,
                        ps_arn,
                        "DIRECT",
                        ""
                    ])
                else:
                    rows.append([
                        "",  # UserName inconnu
                        principal_id,
                        "",
                        "",
                        acct_id,
                        acct_name,
                        ps_name,
                        ps_arn,
                        "DIRECT",
                        ""
                    ])

            elif principal_type == "GROUP":
                gname = groups.get(principal_id, principal_id)
                member_ids = group_members.get(principal_id, set())
                for uid in member_ids:
                    uinfo = users.get(uid, {"UserName": "", "DisplayName": "", "Email": ""})
                    rows.append([
                        uinfo["UserName"],
                        uid,
                        uinfo["DisplayName"],
                        uinfo["Email"],
                        acct_id,
                        acct_name,
                        ps_name,
                        ps_arn,
                        "GROUP",
                        gname
                    ])

# ---------- Tri par UserName ----------
rows.sort(key=lambda r: r[0] or "")

# ---------- Nom du fichier avec date ----------
today_str = date.today().strftime("%Y%m%d")
OUT_FILE = f"{today_str}_identity_center_users_permissions.csv"

# ---------- Sortie CSV ----------
with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "UserName", "UserId", "DisplayName", "Email",
        "AccountId", "AccountName",
        "PermissionSetName", "PermissionSetArn",
        "AssignmentType", "GroupName"
    ])
    w.writerows(rows)

print(f"OK -> {OUT_FILE} ({len(rows)} lignes)")
