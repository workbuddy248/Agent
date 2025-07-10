# Fabric Settings Workflow - Get Details of Single Fabric

## Workflow Metadata
workflow_type: query
dependencies: [login_flow]
can_run_standalone: true
requires_existing_fabric: true
estimated_duration: 30
parameters:
  required: [fabric_name]
  optional: [timeout]

## Test Cases (Write Tests First)

test_navigate_to_fabric_sites
Given: User is logged into DNA home page and sees 'Welcome to Catalyst Center!' text
When: The user clicks on collapsible hamburger menu icon at the top left below the header
When: The user clicks on menu item 'Provision' button
When: The user clicks on 'Fabric Sites' option under 'SD Access'
When: The user is navigated to Fabric Sites Summary Page
Then: The user should see 'SUMMARY' text section
Then: The user should see numeric value or number shown above 'Fabric sites' text

test_access_specific_fabric_details
Given: User is on Fabric Sites Summary Page
When: The user clicks on the numeric value or number shown above 'Fabric sites' text and below 'SUMMARY' text
When: The user clicks on {{fabric_name}}
When: The user is navigated to 'Fabric Infrastructure' header panel
Then: The fabric details page should load successfully
Then: The user should see 'Fabric Infrastructure' header panel
Then: The fabric name {{fabric_name}} should be displayed correctly

test_view_fabric_settings
Given: User is on the Fabric Infrastructure page for {{fabric_name}}
When: The user clicks 'Settings' header panel button
Then: The fabric settings page should load successfully
Then: The settings panel should display configuration details for {{fabric_name}}
Then: The user should be able to take screenshot of the settings page
Then: All fabric configuration parameters should be visible and readable