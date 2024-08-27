#/bin/bash
echo "UserName","GivenName","FamilyName","Email1","Email2" > "$(date +%Y%m%d%H%M)_SSO-ReportUserList.csv"
aws identitystore list-users --identity-store-id $SSOID | jq -r '.Users[] | [.UserName, .Name.GivenName, .Name.FamilyName, (.Emails[].Value)] |  @csv' >> "$(date +%Y%m%d%H%M)_SSO-ReportUserList.csv"
