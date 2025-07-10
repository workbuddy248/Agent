# Inventory Workflow - Device Import and Provisioning

## Workflow Metadata
workflow_type: creation
dependencies: [login_flow, network_hierarchy_creation]
can_run_standalone: false
requires_existing_fabric: false
estimated_duration: 300
parameters:
  required: [file_name, building_name]
  optional: [timeout, wait_time]

## Test Cases (Write Tests First)

test_import_devices_from_file
Given: User is logged into DNA home page and sees 'Welcome to Catalyst Center!' text
When: The user clicks on collapsible hamburger menu icon at the top left below the header
When: The user clicks on menu item 'Provision' button
When: The user clicks on 'Inventory' option under Network Devices
When: The user is navigated to Provision / Inventory Page
When: The user clicks on '+Add device' button
When: The user clicks on 'Import Inventory' button or option
When: The user clicks on 'Click or drag file to this area to upload' button
When: The macOS file picker dialog opens, user clicks on Downloads option
When: The user looks for the {{file_name}} by scrolling and selects the file and clicks on open button
When: The macOS file picker dialog closes and user clicks on 'Next' button
When: The user clicks on Import Devices button
Then: The system should show 'Done!' and 'Devices imported successfully' text on page
Then: The user should be able to click on 'View Inventory' button

test_assign_devices_to_site
Given: Devices have been imported successfully and user is on Provision / Inventory Page
When: The user selects the checkbox select all for column header on the table
When: The user clicks on 'Actions' and from dropdown list clicks on 'Provision' and then on 'Assign device to Site' button
When: The user clicks 'choose a site' button on Assign Device to Site dialog
When: The user opens expansion arrow of all, selects the {{building_name}} and clicks on 'Save' button
When: The user clicks on 'Next' button
When: The user clicks on 'Next' button again
When: The user selects or chooses 'Now' option and clicks on 'Assign' button
When: The user clicks on 'Submit' button
Then: The user should be navigated back to Provision / Inventory Page
Then: The devices should be assigned to {{building_name}}

test_provision_assigned_devices
Given: Devices have been assigned to {{building_name}} and user is on Provision / Inventory Page
When: The user waits for 180 seconds for assignment to complete
When: The user selects the checkbox select all for column header on the table
When: The user clicks on 'Actions' and from dropdown list clicks on 'Provision' and then on 'Provision Device' button
When: The user is navigated to Provision Devices page
When: The user clicks on 'Next' button
When: The user clicks on 'Next' button again
When: The user clicks on 'Next' button again
When: The user selects or chooses 'Now' option and clicks on 'Apply' button
Then: The system should show "Task Submitted" message
Then: The device provisioning process should be initiated successfully