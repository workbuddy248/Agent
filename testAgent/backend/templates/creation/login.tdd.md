Test Cases (Write Tests First)
test_valid_login
Given: User with a valid username and password
When: The user click on the login in button.
Then: The system should land into the home page on successful login
Then: The system should check the title element be present in the home page
test_invalid_login
Given: User with an invalid username and password
When: The user click on the login in button.
Then: The system should see an error "Sign in failed" on unsuccessful login