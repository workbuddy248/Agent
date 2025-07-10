# Login Flow Workflow

## Workflow Metadata
workflow_type: creation
dependencies: []
can_run_standalone: true
requires_existing_fabric: false
estimated_duration: 30
parameters:
  required: [username, password, cluster_url]
  optional: [timeout]

## Test Cases (Write Tests First)

test_valid_login
Given: User with a valid username {{username}} and password {{password}}
When: The user navigates to {{cluster_url}} login page
When: The user enters credentials and clicks login button
Then: The system should land into the home page on successful login
Then: The system should check the title element be present in the home page

test_invalid_login
Given: User with an invalid username and password
When: The user click on the login in button.
Then: The system should see an error "Sign in failed" on unsuccessful login
