# Network Hierarchy Creation Workflow

## Workflow Metadata
workflow_type: creation
dependencies: [login_flow]
can_run_standalone: false
requires_existing_fabric: false
estimated_duration: 45
parameters:
  required: [area_name, building_name]
  optional: [timeout, address]

## Test Cases (Write Tests First)

test_create_area_under_global
Given: User is logged into DNA home page and sees 'Welcome to Catalyst Center!' text
When: The user clicks on collapsible hamburger menu icon at the top left below the header
When: The user clicks on menu item 'Design' button
When: The user clicks on menu item 'Network Hierarchy' under Design and is navigate to the Network Hierarchy page
When: The user verifies 'Global' is present
When: The user clicks on "more options" or "overflow menu" for Global
When: The user clicks 'Add Area' button
When: The user enters Area Name: {{area_name}}
When: The user clicks on 'Add' button
Then: The system should show success confirmation with "Area Added Successfully"
Then: The user should see {{area_name}} under Global scope

test_create_building_under_area
Given: Area {{area_name}} exists under Global scope
When: The user clicks on expansion arrow of Global
When: The user sees {{area_name}} and clicks on "more options" or "overflow menu" for {{area_name}}
When: The user clicks 'Add Building' button
When: The user enters Building Name: {{building_name}}
When: The user enters "Sanjose" in Address field and selects first option from dropdown
When: The user clicks on 'Add' button
Then: The system should show success confirmation with "Site Added Successfully"
Then: The building {{building_name}} should be visible under area {{area_name}}

test_verify_hierarchy_structure
Given: Area {{area_name}} and building {{building_name}} have been created
When: The user views the Network Hierarchy page
Then: The hierarchy should show Global → {{area_name}} → {{building_name}}
Then: All hierarchy levels should be expandable and collapsible
Then: The created structure should be persistent and visible on page refresh