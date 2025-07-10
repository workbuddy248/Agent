# Fabric Creation Workflow - Create New Fabric Site

## Workflow Metadata
workflow_type: creation
dependencies: [login_flow, network_hierarchy_creation, inventory_workflow]
can_run_standalone: false
requires_existing_fabric: false
estimated_duration: 180
parameters:
  required: [building_name, device_group_name_in_order, device_group_counts]
  optional: [timeout, bgp_asn, area_name]

## Test Cases (Write Tests First)

test_initiate_fabric_creation
Given: User is logged into DNA home page and sees 'Welcome to Catalyst Center!' text
When: The user clicks on collapsible hamburger menu icon at the top left below the header
When: The user clicks on menu item 'Provision' button
When: The user clicks on 'Fabric Sites' option under 'SD Access'
When: The user is navigated to Fabric Sites Page
When: The user clicks on the 'Create Fabric Sites and Device groups' button
When: The Create Fabric Site dialog opens
When: The user clicks on 'Let's Do It' button
Then: The user should be navigated to Fabric Site Location page
Then: The location selection interface should be displayed

test_select_fabric_location
Given: User is on Fabric Site Location page
When: The user selects the {{building_name}} by clicking on the expansion arrow of Global and {{area_name}}
When: The user clicks on 'Save and Next' button
When: The system shows 'Network Creation Successfully completed'
When: The user clicks on 'Save and Next' button
Then: The device assignment page should be displayed
Then: The user should see devices listed under column header 'Device Name' on the table

test_assign_device_groups
Given: User is on device assignment page with available devices
When: The user selects checkbox of first device under column header 'Device Name' on the table
When: The user clicks on 'Assign Device Group' button
When: The Assign Device Group dialog opens, user clicks on expansion or dropdown arrow
When: The user selects 'Border' and clicks on 'Save' button
When: The user selects checkbox of second device under column header 'Device Name' on the table
When: The user clicks on 'Assign Device Group' button
When: The Assign Device Group dialog opens, user clicks on expansion or dropdown arrow
When: The user selects 'Leaf' and clicks on 'Save' button
When: The user selects checkbox of third device under column header 'Device Name' on the table
When: The user clicks on 'Assign Device Group' button
When: The Assign Device Group dialog opens, user enters 'Spine' in the search box on expansion or dropdown arrow
When: The user selects 'Spine' and clicks on 'Save' button
When: The user clicks on 'Save and Next' button
Then: The system should show success confirmation
Then: All devices should be assigned to their respective device groups (Border, Leaf, Spine)

test_configure_bgp_and_deploy
Given: Device groups have been assigned successfully
When: The user enters 1200 in BGP ASN textbox
When: The user clicks on 'Next' button
When: The user clicks on 'Next' button again
When: The user clicks 'Deploy' button
When: The user clicks on 'Next' button
When: The user waits for the deploy button to be enabled and takes screenshot when enabled
When: The user clicks on 'Deploy' button
When: The user clicks on 'Submit' button
Then: The deployment process should be initiated successfully
Then: The user should see deployment progress indicators

test_verify_fabric_creation_completion
Given: Fabric deployment has been submitted
When: The user waits till he is navigated and page loads
When: The user sees 'Done! You Have Created Fabric Site' text on the page
When: The user clicks on 'View All Fabric Sites' button
When: The user is navigated to the fabric sites page
When: The user takes screenshot
Then: The newly created fabric site for {{building_name}} should be visible
Then: The fabric should show as successfully created and deployed
Then: All assigned device groups should be properly configured and operational