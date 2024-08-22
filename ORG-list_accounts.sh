#/bin/bash
echo "Id","Name","Status","JoinedTimestamp" > "$(date +%Y%m%d)_AWSOrg_all_accounts.csv"
aws organizations list-accounts | jq -r '.Accounts[] | [.Id, .Name, .Status, .JoinedTimestamp] |@csv' >> "$(date +%Y%m%d)_AWSOrg_all_accounts.csv"
