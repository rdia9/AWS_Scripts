#/bin/bash
echo "Please enter the AWS SSO CLI Profile with privileges :"
read profile_aws
echo "UserName","GivenName","FamilyName","Email1","Email2" > "$(date +%Y%m%d%H%M)_SSO-ReportUserList.csv"
aws identitystore list-users --profile ${profile_aws} --identity-store-id $SSOID | jq -r '.Users[] | [.UserName, .Name.GivenName, .Name.FamilyName, (.Emails[].Value)] |  @csv' >> "$(date +%Y%m%d%H%M)_SSO-ReportUserList.csv"
