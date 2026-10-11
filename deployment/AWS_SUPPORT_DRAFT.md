# CloudFront account verification request (draft, not submitted)

Account: 137181255781. Account email supplied by operator: harshikathopte@gmail.com.

Please verify this AWS account for CloudFront distribution creation. I am deploying a small Air Guardian school pilot with a private S3 origin, HTTPS CloudFront hosting, Cognito, Lambda and DynamoDB in ap-south-1. A USD 10 monthly AWS Budget is configured. SMS/WhatsApp and optional IoT sensors are disabled.

CloudFormation resource `Distribution` failed with:

> Your account must be verified before you can add new CloudFront resources. To verify your account, please contact AWS Support (https://console.aws.amazon.com/support/home#/) and include this error message.

Service: CloudFront. HTTP status: 403. Request ID: b59b3faa-7393-4a13-a592-7622c79c108f.

Open [AWS Support](https://console.aws.amazon.com/support/home#/) and complete the requested account verification. No support case has been submitted by the assistant. After approval, set `EnableWebsiteHosting: 'true'` in `deployment/pilot.parameters.yaml` and rerun deployment to activate the prepared private S3/CloudFront site.
